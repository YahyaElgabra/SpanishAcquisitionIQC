from spacq.tool.box import flatten
from time import sleep, time
from threading import Condition, Thread
from itertools import repeat
from functools import partial, wraps
import logging
log = logging.getLogger(__name__)


def update_current_f(f):
    @wraps(f)
    def wrapped(self):
        self.current_f = f.__name__

        log.debug('Entering function: {0}'.format(self.current_f))

        return f(self)

    return wrapped


class PulseConfiguration(object):
    """
    The configuration necessary to execute a pulse program with a device.
    """

    # All the directly-used attributes.
    awg_attrs = ['channels', 'clear_channels', 'enabled',
                 'run_mode', 'sampling_rate', 'trigger']
    oscilloscope_attrs = ['acquiring', 'fastframe',
                          'fastframe_count', 'fastframe_sum', 'stopafter']

    @staticmethod
    def verify_device(name, device, attributes):
        if device is None:
            raise TypeError('No "{0}" device configured'.format(name))

        d = dir(device)

        for attribute in attributes:
            if attribute not in d:
                raise TypeError(
                    'Given "{0}" device lacks "{1}"'.format(name, attribute))

    def __init__(self, program, channels, awg, oscilloscope):
        self.verify_device('AWG', awg, self.awg_attrs)
        self.verify_device('Oscilloscope', oscilloscope,
                           self.oscilloscope_attrs)

        self.program = program
        self.channels = channels
        self.awg = awg
        self.oscilloscope = oscilloscope


class SweepController(object):
    """
    A simple controller for a sweep of several variables.

                                                                                                                     conditional_dwell
                                                                                                                            v       ^
    init -> next -> transition -> write -> dwell -> pulse -> read -> condition -> ramp_down -> end
    ^       ^                                  |_____________^           |             |
    |       |____________________________________________________________|             |
    |__________________________________________________________________________________|	

    """

    def __init__(self, resources, variables, num_items, measurement_resources, measurement_variables,
                 condition_resources=[], condition_variables=[], pulse_config=None, continuous=False):
        self.resources = resources
        self.variables = variables
        self.num_items = num_items
        self.measurement_resources = measurement_resources
        self.measurement_variables = measurement_variables
        # TODO: Instead of flattening, make use of the group ordering for quicker access
        self.condition_resources = [
            cond_tuple for cond_tuple in flatten(condition_resources)]
        self.condition_variables = condition_variables
        self.pulse_config = pulse_config
        self.continuous = continuous

        # The callbacks should be set before calling run(), if necessary.
        self.data_callback, self.close_callback, self.write_callback, self.read_callback = [
            None] * 4
        self.general_exception_handler = None
        self.resource_exception_handler = None

        self.devices_configured = False

        self.current_f = None

        self.item = -1

        self.paused = False
        self.pause_lock = Condition()

        self.last_continuous = False
        self.done = False
        self.aborting = False
        self.abort_fatal = False

        self.sweep_start_time = time()
        self.first_time_point = None

        self.orders = [vars[0].order for vars in self.variables]
        self.orders.reverse()
        self.condition_orders = [
            group[0].order for group in self.condition_variables]
        self.conditional_wait = 0
        self.order_periods = None

    def compute_order_periods(self):
        """
        This function computes the number of elements iterated before each order changes.
        """
        periods = []
        orders = []

        for group in reversed(self.variables):
            # skip if vars in group are consts.
            if group[0].use_const != 1:
                num_in_group = None

                # get the length of the group
                for var in group:
                    num_in_var = len(var)

                    if num_in_group is None or num_in_var < num_in_group:
                        num_in_group = num_in_var

                # append the period of this group and its order.
                if not periods:
                    periods.append(num_in_group)
                else:
                    periods.append(periods[-1]*num_in_group)

                orders.append(group[0].order)

        for order in self.condition_orders:
            if order not in orders:
                orders.append(order)
                orders.sort()
                new_index = orders.index(order)
                if new_index > 0:
                    periods.insert(new_index, periods[new_index - 1])
                else:  # if the condition is the smallest order, it has a period of 1
                    periods.insert(new_index, 1)

        # create a dict.
        self.order_periods = dict(list(zip(orders, periods)))

    def create_iterator(self, pos):
        """
        Create an iterator for an order of variables.
        """

        return zip(*(iter(var) for var in self.variables[pos]))

    def ramp(self, resources, values_from, values_to, steps):
        """
        Slowly sweep the resources.
        """

        thrs = []
        for (name, resource), value_from, value_to, resource_steps in zip(resources,
                                                                          values_from, values_to, steps):
            if resource is None:
                continue

            kwargs = {}
            if self.resource_exception_handler is not None:
                kwargs['exception_callback'] = partial(
                    self.resource_exception_handler, name, write=True)

            thr = Thread(target=resource.sweep, args=(
                value_from, value_to, resource_steps), kwargs=kwargs)
            thrs.append(thr)
            thr.daemon = True
            thr.start()

        for thr in thrs:
            thr.join()

    def write_resource(self, name, resource, value):
        """
        Write a value to a resource and handle exceptions.
        """

        try:
            resource.value = value
        except Exception as e:
            if self.resource_exception_handler is not None:
                self.resource_exception_handler(name, e, write=True)
            return

    def read_resource(self, name, resource, save_callback):
        """
        Read a value from a resource and handle exceptions.
        """

        try:
            value = resource.value
        except Exception as e:
            if self.resource_exception_handler is not None:
                self.resource_exception_handler(name, e, write=False)
            return

        save_callback(value)

    def run(self, next_f=None):
        """
        Run the sweep.
        """

        try:
            if next_f is None:
                next_f = self.init

            # Trampoline.
            while next_f is not None:
                f_name = next_f.__name__

                if self.paused:
                    log.debug('Paused before function: {0}'.format(f_name))

                    with self.pause_lock:
                        self.pause_lock.wait()

                if self.aborting:
                    log.debug('Aborting before function: {0}'.format(f_name))

                    if not self.abort_fatal:
                        self.continuous = False
                        self.ramp_down()

                    return

                log.debug('Starting function: {0}'.format(f_name))

                try:
                    next_f = next_f()
                except Exception as e:
                    if self.general_exception_handler is not None:
                        self.general_exception_handler(f_name, e)
                    else:
                        log.exception(
                            'Caught exception in function: {0}'.format(f_name))

                    # Attempt to exit normally at this point.
                    next_f = None
        finally:
            self.end()

    @update_current_f
    def init(self):
        """
        Initialize values and possibly devices.
        """

        self.iterators = None
        self.current_values = None
        self.last_values = None

        self.item = -1

        self.compute_order_periods()

        if not self.devices_configured:
            log.debug('Configuring devices')

            if self.pulse_config is not None:
                # AWG
                awg = self.pulse_config.awg

                awg.enabled = False
                awg.sampling_rate = self.pulse_config.program.frequency
                awg.run_mode = 'triggered'

            self.devices_configured = True

        return self.next_values

    @update_current_f
    def next_values(self):
        """
        Get the next set of values from the iterators.
        """

        self.item += 1
        if self.current_values is not None:
            self.last_values = self.current_values[:]

        if self.iterators is None:
            # First time around.
            self.iterators = []
            for pos in range(len(self.variables)):
                self.iterators.append(self.create_iterator(pos))

            self.current_values = [next(it) for it in self.iterators]
            self.changed_indices = list(range(len(self.variables)))

            # Calculate where the end of each order is.
        else:
            pos = len(self.variables) - 1
            while pos >= 0:
                try:
                    self.current_values[pos] = next(self.iterators[pos])
                    break
                except StopIteration:
                    self.iterators[pos] = self.create_iterator(pos)
                    self.current_values[pos] = next(self.iterators[pos])

                    pos -= 1

            self.changed_indices = list(range(pos, len(self.variables)))

        return self.transition

    @update_current_f
    def transition(self):
        """
        Perform a transition for variables, as required.
        """

        if self.last_values is None:
            # Smooth set from const.
            steps, resources, from_values, to_values = [], [], [], []

            for pos in range(len(self.variables)):
                # Extract values for this group.
                group_vars, group_resources, current_values = (self.variables[pos],
                                                               self.resources[pos], self.current_values[pos])

                for var, resource, current_value in zip(group_vars, group_resources,
                                                        current_values):
                    if var.use_const or not var.smooth_from:
                        continue

                    steps.append(var.smooth_steps)
                    resources.append(resource)
                    from_values.append(var.with_type(var.const))
                    to_values.append(current_value)

            self.ramp(resources, from_values, to_values, steps)
        else:
            # The first changed group is simply stepping; all others rolled over.
            affected_groups = self.changed_indices[1:]

            steps, resources, from_values, to_values = [], [], [], []

            for pos in affected_groups:
                # Extract values for this group.
                group_vars, group_resources, current_values, last_values = (self.variables[pos],
                                                                            self.resources[pos], self.current_values[pos], self.last_values[pos])

                for var, resource, current_value, last_value in zip(group_vars, group_resources,
                                                                    current_values, last_values):
                    if var.use_const or not var.smooth_transition:
                        continue

                    steps.append(var.smooth_steps)
                    resources.append(resource)
                    from_values.append(last_value)
                    to_values.append(current_value)

            self.ramp(resources, from_values, to_values, steps)

        return self.write

    @update_current_f
    def write(self):
        """
        Write the next values to their resources.
        """

        thrs = []
        for pos in self.changed_indices:
            for i, ((name, resource), value) in enumerate(zip(self.resources[pos], self.current_values[pos])):
                if resource is not None:
                    thr = Thread(target=self.write_resource,
                                 args=(name, resource, value))
                    thrs.append(thr)
                    thr.daemon = True
                    thr.start()

                if self.write_callback is not None:
                    self.write_callback(pos, i, value)

        for thr in thrs:
            thr.join()

        return self.dwell

    @update_current_f
    def dwell(self):
        """
        Wait for all changed variables.
        """

        delay = max(
            var._wait.value for pos in self.changed_indices for var in self.variables[pos])
        sleep(delay)

        if self.pulse_config is not None:
            return self.pulse
        else:
            return self.read

    @update_current_f
    def pulse(self):
        """
        Run through the pulse program.
        """

        if self.pulse_config.channels:
            waveforms = self.pulse_config.program.generate_waveforms()
            times = self.pulse_config.program.times_average

            # AWG
            awg = self.pulse_config.awg
            awg.enabled = False

            awg.clear_channels()

            channels = []
            for output, number in list(self.pulse_config.channels.items()):
                channel = awg.channels[number]

                waveform, markers = waveforms[output]
                channel.set_waveform(waveform, markers, name=output)

                channels.append(channel)

            for channel in channels:
                channel.enabled = True

            awg.enabled = True

            # Oscilloscope
            osc = self.pulse_config.oscilloscope
            osc.acquiring = False

            if times > 1:
                osc.fastframe = True
                osc.fastframe_sum = 'average'
                osc.fastframe_count = times + 1

                if osc.fastframe_count != times + 1:
                    raise ValueError(
                        'Cannot average {0} times; check the oscilloscope'.format(times))
            else:
                osc.fastframe = False

            osc.stopafter = 'sequence'

            awg.opc
            osc.opc

            osc.acquiring = True
            # Wait for the oscilloscope to ready the trigger.
            sleep(1)

            # All together now!
            trigger = awg.trigger
            delay = self.pulse_config.program.acq_delay.value

            for _ in repeat(None, times):
                trigger()
                awg.opc

                end_time = time() + delay
                time_diff = end_time - time()
                while time_diff > 0:
                    sleep(time_diff)
                    time_diff = end_time - time()

            osc.opc

            acqs = osc.acquisitions
            if acqs != times:
                raise ValueError(
                    'Incorrect number of acquisitions made: {0}'.format(acqs))

        return self.read

    @update_current_f
    def read(self):
        """
        Take measurements.
        """
        measurements = [None] * len(self.measurement_resources)

        thrs = []
        for i, (name, resource) in enumerate(self.measurement_resources):
            if resource is not None:
                def save_callback(value, i=i):
                    measurements[i] = value
                    if self.read_callback is not None:
                        self.read_callback(i, value)

                thr = Thread(target=self.read_resource,
                             args=(name, resource, save_callback))
                thrs.append(thr)
                thr.daemon = True
                thr.start()

        for thr in thrs:
            thr.join()

        if self.data_callback is not None:
            if self.first_time_point is None:
                cur_time = 0
                self.first_time_point = time()
            else:
                cur_time = time() - self.first_time_point

            self.data_callback(cur_time, tuple(
                flatten(self.current_values)), tuple(measurements))

        return self.condition

    @update_current_f
    def condition(self):
        """
        Stalls an order's loop (after the order's variables have been exhausted)
        with repeated measurements until conditions are true.
        Once conditions are true, then the sweep controller moves on to the next order
        and continues as usual.
        """
        boolean = True

        if self.condition_variables:

            # Find the orders that have changed
            orders_changed = []
            for order in list(self.order_periods.keys()):
                if (self.item + 1) % self.order_periods[order] == 0:
                    orders_changed.append(order)
            orders_changed.sort()

            # The wait time is defined by the max of the wait times of the lowest triggered order of condition variables
            self.conditional_wait = 0
            for order in orders_changed:
                if order in self.condition_orders:
                    corresponding_index = self.condition_orders.index(order)
                    for var in self.condition_variables[corresponding_index]:
                        if var._wait.value > self.conditional_wait:
                            self.conditional_wait = var._wait.value
                    break

            # Check the conditions for the changed orders, starting from the lowest order.
            for order in orders_changed:
                if order in self.condition_orders:
                    for var in self.condition_variables[self.condition_orders.index(order)]:
                        boolean_to_compound = var.evaluate_conditions(
                            self.condition_resources)
                        boolean = boolean and boolean_to_compound

        if boolean == True:
            if self.item == self.num_items - 1:
                self.item += 1
                return self.ramp_down
            else:
                return self.next_values
        if boolean == False:
            return self.conditional_dwell

    def conditional_dwell(self):
        """
        Dwell for the max time defined by the conditions in the current order.
        """
        sleep(self.conditional_wait)
        return self.read

    @update_current_f
    def ramp_down(self):
        """
        Sweep from the last values to const.
        """

        if not self.current_values:
            return

        # Smooth set to const.
        steps, resources, from_values, to_values = [], [], [], []

        for pos in range(len(self.variables)):
            # Extract values for this group.
            group_vars, group_resources, current_values = (self.variables[pos],
                                                           self.resources[pos], self.current_values[pos])

            for var, resource, current_value in zip(group_vars, group_resources,
                                                    current_values):
                if var.use_const or not var.smooth_to:
                    continue

                steps.append(var.smooth_steps)
                resources.append(resource)
                from_values.append(current_value)
                to_values.append(var.with_type(var.const))

        self.ramp(resources, from_values, to_values, steps)

        if self.continuous and not self.last_continuous:
            return self.init

    @update_current_f
    def end(self):
        """
        The sweep is over.
        """

        assert not self.done
        self.done = True

        if self.close_callback is not None:
            self.close_callback()

    def pause(self):
        log.debug('Pausing.')

        self.paused = True

        log.debug('Paused.')

    def unpause(self):
        log.debug('Unpausing.')

        with self.pause_lock:
            self.paused = False
            self.pause_lock.notify()

        log.debug('Unpaused.')

    def abort(self, fatal=False):
        """
        Ending abruptly for any reason.
        """

        log.debug('Aborting.')

        self.aborting = True
        self.abort_fatal = fatal

        if self.abort_fatal:
            log.warning('Aborting fatally.')

        self.unpause()
