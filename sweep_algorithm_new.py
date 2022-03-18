from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
# Partially completed functions related to RF pumping

def pumping_single_sweep(v_pp_val, v_ent_vals, V_pp_Instrument, V_ent_Instrument, CurrentReader, gain, max_current):
    
    # Set V_pp
    V_pp_Instrument.typeNAmplitude = v_pp_val

    # Initialize list that will store currents
    currents = []

    # Get 1D sweep over v_ent_vals
    for v_ent_val_ in v_ent_vals:
        
        # Set value of v_ent and then measure the current and save for later
        V_ent_Instrument.voltage = v_ent_val_
        current = _get_current(CurrentReader, gain)

        # Check that current is not exceeding maximum current and that 
        if current.value <= max_current:
            raise ValueError("Current value exceeding max current allowed. Aborting sweep")

        # Check that current is not negative, which indicates that the channel is fully opened
        if current.value <= 0:
            raise ValueError("Current value less than 0, which indicates that the channel is fully opened. Aborting sweep")

        # If both thosse checks are good, add current to list
        currents.append(current)
    
    ## If no issues arise, we can perform analysis on the acquired currents
    
    # Initialize empty lists that will be used for analysis
    x = []
    y = []

    # Go over all currents 
    for i in range(len(currents)):

        # Add to the x and y range until the scanning window is the correct size
        x.append(v_ent_vals[i])
        y.append(currents[i])

        # Once the scanning window is reached, start doing analysis
        if len(x) == scan_range:

                # Try all the possible values of plateaus you have
                for n in range(1,max_plateaus):

                    # Define a gloabl variable that is used for fitting 
                    # TODO Make this better
                    global N
                    N = n - 1

                    # Checks that plateau is near the middle of the scan range
                    cond1 = (abs(y[scan_range/2] - n*e*frequency*(1e9)) < 0.002)

                    # Checks that the value of the plateau is near the expected value
                    cond2 = True not in [(abs(y[i] - n*e*frequency*(1e9)) > plateau_tol) for i in range(scan_range)]

                    # Checks that derivative (difference between 2 data points) is not too large where the data is supposed to be flat
                    rec3 = np.abs(np.diff(x)) < epsilon
                    cond3 = False not in rec3

                    # Makes sure that all 3 conditions are met before starting the 
                    if cond1 and cond2 and cond3:

                        # Initial conditions are set differently depending on whether current in increasing or decreasing
                        if y[0] > y[scan_range-1]:
                            initial = [-2.5, -2.5*x[0], -2.5*x[scan_range-1]]
                        else:
                            initial = [2.5, 2.5*x[0], 2.5*x[scan_range-1]]

                        # Perform fit with initial conditions
                        delta, error, p, _ = perform_fit(x,y,initial,n)
                        if error < fit_error:
                            print "========================================"
                            print 'delta: ',str(delta),'error: '+str(error)
                            print('initial_vals: {}'.format(initial))
                            print('best_vals: {}'.format(p))
                            print "========================================\n"
                            plot_plateau(x,y,p,n,Vdc)

                # Remove the first data point from the window so the window gets shifted
                x.pop(0)
                y.pop(0)

def rf_optimization(v_pp_vals, v_ent_vals, v_ext_vals, V_pp_Instrument, V_ent_Instrument, V_ext_Instrument, CurrentReader, gain, frequency, max_plateau_current):
    '''
    Algorithm which determines a triplet of values for V_ent, V_ext and V_pp which generates pumping.

    Parameters:
    v_pp_vals : Interable of numbers in Volts that we wish v_pp to sweep over. 
    v_ent_vals : Interable of numbers in Volts that we wish v_ent to sweep over. 
    v_ext_vals : Interable of numbers in Volts that we wish v_ext to sweep over. 
    V_pp_Instrument : Device object that is used to to adjust V_pp. 
                    Must have a setter/getter attribute called 'TODO' and 'frequency'
    V_ent_Instrument : Device object that is used to to adjust V_ent. 
                    Must have a setter/getter attribute called 'voltage'
    V_ext_Instrument : Device object that is used to to adjust V_ext.
                    Must have a setter/getter attribute called 'voltage'
    CurrentReader: Device object that is used to read current. Must have an attribute called 'reading'. 
                It is assumed that we will be using a current preamp, which converts from current to voltage
    gain: Gain of current preamp. Used to convert from current through device to voltage.
    frequency : Frequency in Hertz of the signal generated by V_pp_Instument
    max_plateau_current: Maximum current allowed in terms of plateaus. So I_max = max_plateau_current * electron_charge * frequency

    Returns:
    pumping_point or None: Dictionary with 3 elements (v_pp, v_ent and v_ext) where resonable pumping occured.
                        If no pumping is detected, return None.
    '''

    # Calculate the maximum current allowed through the device
    electron_charge = 1.60217662 * 10**-19
    max_current = Quantity(max_plateau_current * electron_charge * frequency, 'A')

    # Set frequency of signal generator to desrired value
    V_pp_Instrument.frequancy = frequency

    # Loop over possible v_ext_vals
    for v_ext_ in v_ext_vals:

        # Set v_ext to value
        V_ext_Instrument.voltage = v_ext_

        # Now sweep over the various v_pp values
        for v_pp_val_ in v_pp_vals:

            # Now do a single sweep of v_ent, with a fixed v_pp and a fixed v_ext, storing the ouput to a temporary variable
            temp = pumping_single_sweep(v_pp_val_, v_ent_vals, V_pp_Instrument, V_ent_Instrument, CurrentReader, gain, max_current)

            # If temp is not None, then we believe that we have found pumping. Save these values in a dictionary and return it
            if temp is not None:
                pumping_point = dict()
                pumping_point['v_ext'] = v_ext_
                pumping_point['v_pp'] = v_pp_val_
                return pumping_point

def f(x, a, d1, d2):
    """
    Function for fitting <n> plateaus

    y = exp(-exp(-a*(x-c)+d1)) + exp(-exp(-a*(x-c)+d2)) + In

    a controls the steepness
    d1, d2 control the offsets of the two exponentials
    d is a bias current
    n_i = current values for n
    diff = d1 - d2 controls the extent of the plateau in the middle

    For parameters between 1 and 100, added conversion factors
    all paramters are positive in function
    
    """
    A = 10*a
    D1 = 10*d1
    D2 = 10*d2
    y = e * (frequency) * (1e9) * ( np.exp(-np.exp(-A*x+D1)) + np.exp(-np.exp(-A*x+D2)) + N)
    return y

def plot_plateau(x,y,p,n,Vdc):
    """
        Wrapper to plot the results one at a time
    """
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_xlabel('Vrf [V]')
    ax.set_ylabel('Current [nA]')
    fig.suptitle('Vdc = '+str(Vdc)+' n = '+str(n), fontsize=24)
    
    plt.plot(x,y,'x',label='Experimental data')     
    t = np.linspace(min(x),max(x),1000)
    plt.plot(t,f(t,p[0],p[1],p[2]),label='Fit')
    plt.axhline(y=n*e*frequency*1e9, color='black', linestyle='-')

    ax.legend()
    plt.show(block=True)
    plt.pause(0.3)
    plt.close()
    
    return None

def perform_fit(xdata,ydata,initial,n):
    """
        This function performs a fit using the logistic function

        Inputs: xdata (array), ydata (array), inital (array), n (int)

        xdata: array of floats to fit
        ydata: array of floats to fit
        initial: [a_0, d1_0, d2_0]
        n: integer number of current plateau to be evaluated

    """
    try:
        p, pcov = curve_fit(f,xdata,ydata,p0=initial)
        delta = p[2]-p[1]
        error = sum([ abs(ydata[i] - f(xdata[i],p[0],p[1],p[2])) for i in range(len(xdata)) ])
    except:
        print "ERROR: RuntimeError: Optimal parameters not found: Number of calls to function has reached maxfev"
        return 0, 0, [0,0,0,0], [0]
    return abs(delta), error, p, pcov