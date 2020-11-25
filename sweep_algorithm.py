############################################################################################################################
# sweep_algorithm()                                                                                                        #
# This function solves intiates a sweep based on data to tune the pumping procedure                                        #
# Andres Lombo 2020-10-10                                                                                                  #
############################################################################################################################
"""

    Control steps:

    1. Turn on Rf component of Vrf
    2. Fix Vdc and sweep Vrf at different Vpp for the RF amplitude
    3. If above expedcted current plateau and no plateaus, step Vdc and try again
    4. If Vdc is stepped and no plateaus, reduce Vqpc
    5. Repeat until plateaus are formed

    Libary versions: 
    numpy 1.16.6
    matplotlib 2.2.5
    scipy 1.2.3
    lmfit 0.9.15

    current in [nA], voltage in [V]

""" 

import numpy as np
import matplotlib.pyplot as plt
from scipy.constants import e
import csv
from scipy.optimize import curve_fit

def get_current(Vrf, Vdc):

    """ 
        FIX THIS FUNCTION 

        This function returns the current value for a given (Vrf, Vdc)
        It also records the history of Vrf, Vdc, and I accessed
        To be replaced with acutal interface

        Inputs: Vrf (float), Vdc (float)

        Outputs: I (float)

    """
    current = current_dict[Vrf,Vdc]
    history.append([Vrf,Vdc,current])
    return current

def turn_on_rf_component_of_Vrf(RF):
    """ 
        FIX THIS FUNCTION 

        This function turns on the RF component of VRF at a fiven value

        Inputs: RF (float)
    """
    return RF

def set_Vdc(Vdc):
    """ 
        FIX THIS FUNCTION

        This function fixes Vdc at a given value

        Inputs: Vdc (float)
     """

    return Vdc

def set_Vrf(Vrf):
    """ 
        FIX THIS FUNCTION

        This function fixes Vrf at a given value

        Inputs: Vrf (float)
     """

    return Vrf

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

def find_plateau(Vrf_array,Vdc_array,scan_range,plateau_tol,epsilon,frequency,fit_error, max_plateaus):

    """
    This funciton finds the plateau in the current by fitting a logistic function

    Inputs: Vrf_params (array), Vdc_params (array), scan_range (float), plateau_tol (float), epsilon (float), frequency (float), fit_error: (float)
        Vrf_array = array of Vrf values to sweep (float) [V]
        Vdc_array = array of Vdc values to sweep (float) [V]
        scan_range: number of data points for fit
        plateau_tol: plateau tolerance [nA]
        epsilon: tolerance for F'(X) [nA/V]
        frequency: obvious [Hz]

    Outputs: [Vrf_final, Vdc_final] (array)

    After a Vdc is set, the algorithm will set Vrf from 0 to Vrf_params[0]
    Then Vrf is going to be swep  get a data range that is {scan_range}

    Errors: 
        -1: Sweeping outside allowed scan range
        -2: Not enough data points in a sweep to perform fit

    """
    # Turn on RF component of Vrf
    dummy = turn_on_rf_component_of_Vrf(0)

    for Vrf in Vrf_array:                       #--------------- temporary switch ------------------

        # Fix Vrf
        dummy = set_Vrf(Vrf)                    # temporary switch

        x = []
        y = []

        for Vdc in Vdc_array:                   # temporary switch
            dummy = set_Vdc(Vdc)                # temporary switch
            x.append(Vdc)                       # temporary switch
            y.append(get_current(Vrf,Vdc))      
            if len(x) == scan_range:
                for n in range(1,max_plateaus):
                    global N
                    N = n - 1
                    cond1 = (abs(y[scan_range/2] - n*e*frequency*(1e9)) < 0.002)
                    cond2 = True not in [(abs(y[i] - n*e*frequency*(1e9)) > plateau_tol) for i in range(scan_range)]
                    rec3 = np.abs(np.diff(x)) < epsilon
                    cond3 = False not in rec3

                    if cond1 and cond2 and cond3:
                        if y[0] > y[scan_range-1]:
                            initial = [-2.5, -2.5*x[0], -2.5*x[scan_range-1]]
                        else:
                            initial = [2.5, 2.5*x[0], 2.5*x[scan_range-1]]

                        delta, error, p, pcov = perform_fit(x,y,initial,n)
                        if error < fit_error:
                            print "========================================"
                            print 'delta: ',str(delta),'error: '+str(error)
                            print('initial_vals: {}'.format(initial))
                            print('best_vals: {}'.format(p))
                            print "========================================\n"
                            #plot_plateau(x,y,p,n,Vdc)
                x.pop(0)
                y.pop(0)
    return None

### Script implementation

current_dict = {}
history = []

Vrf_array = []
Vdc_array = []

# Create dictionary for curent value lookup
# Note all keys are values with 3 decimal places to avoid rounding issues
with open('SEP_tuning_files/2018-11-23_17-00-39.csv','r') as file:               
    reader = csv.reader(file)
    line_count = 0
    for row in reader:
        if line_count != 0:
            key1 = round(float(row[2])/10,3)                                    # as Vrf data is x10 amplified
            key2 = round(float(row[1])/10,3)                                    # as Vdc data is x10 amplified
            current_dict[(key1,key2)] = float(row[3])

            if key1 not in Vrf_array:
                Vrf_array.append(key1)
            if key2 not in Vdc_array:
                Vdc_array.append(key2)

            #print (key1,key2),float(row[3])
        line_count += 1

# Define constants
frequency = 100e6
#Vrf_array =  [round(0.76+i*(0.007/3),3) for i in range(211)]                 # for older data: [float(x)/1000 for x in range(710,801)] 
#SVdc_array =  [round(0.675+i*(0.0245/17),3) for i in range(171)]              # for older data: [0.001, 0.01, 0.02, 0.04, 0.05]
Vrf_array.sort()
Vdc_array.sort()
scan_range = 17
plateau_tol = 0.015
epsilon = 0.1
fit_error = 0.03
max_plateaus = 5

"""
print '=================================================='
count = 1
for j in Vdc_array:
    for i in Vrf_array:
        print str(count)+':',(i,j), get_current(i,j)
        count = count + 1
"""

find_plateau(Vrf_array,Vdc_array,scan_range,plateau_tol,epsilon,frequency,fit_error, max_plateaus)

