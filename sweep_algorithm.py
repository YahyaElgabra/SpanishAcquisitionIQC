##############################################################
# sweep_algorithm()
# This function solves intiates a sweep based on data to tune the pumping procedure
# Andres Lombo 2020-10-10

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

""" 
import numpy as np
import matplotlib.pyplot as plt
import scipy.signal
import csv

# Separation between successive Vdc and Vrf points in .csv
inc = 0.002
history = []                # problems with cycling before? -> not in the ranges we do

# Create dictionary for curent value lookup
# Note all keys are values with 3 decimal places to avoid rounding issues
current_dict = {}
with open('SEP_tuning_files/2D_sweep_RF_DC.csv','r') as file:               # taken at 1.2Ghz
    reader = csv.reader(file)
    line_count = 0
    for row in reader:
        if line_count != 0:
            key1 = str(round(float(row[0]),3))
            key2 = str(round(float(row[1]),3))
            current_dict[(key1,key2)] = row[2]
            #print(row)
        line_count += 1

def get_current(Vrf, Vdc):

    """ 
        This function returns the current value for a given (Vrf, Vdc)
        It also records the history of Vrf, Vdc, and I accessed
        To be replaced with another interface

        Inputs: Vrf (float), Vdc (float)

        Outputs: I (float)

    """
    current = float(current_dict[(str(round(Vrf,3)),str(round(Vdc,3)))])
    history.append([Vrf,Vdc,current])
    return current

def set_Vrf(i):
    """
        Dummy function for setting Vrf
    """
    return i

def set_Vdc(i):
    """
        Dummy function for setting Vdc
    """
    return i

def reduce_Vqpc(i):
    """
        Dummy function for reducing Vqpc
    """
    return i

def RF_component():
    return True

def measure(Vdc,l,r):
    """
        This function returns an array of current values for a
        sweep of Vrf at a fixed Vdc

        Inputs: Vdc (float), l (float), r (float)
        Outputs: current_array (array)
    """
    current = []
    Vrf_array = np.linspace(l,r,((abs(l-r))/inc)+1)
    for i in Vrf_array:
        Vrf = set_Vrf(i)
        current.append(get_current(Vrf,Vdc))
    return np.asarray(current)

def find_plateau(Vrf_params,Vdc_params,scan_range,frequency,poly_deg,plateau_tol):

    """
    This funciton finds the plateau in the current by looking at polynomial derivatives

    Inputs: Vrf_params (array), Vdc_params (array), scan_range (float), frequency (int), poly_deg (int), plateau_tol (float)
        Vrf_params = [Vrf_start,Vrf_end] (float) [V]
        Vdc_params = [Vdc_start,Vdc_end] (float) [V]
        scan_range: range of scan to find plateau [V]
        frequency: frequency of sweep [Hz]
        poly_deg: degree of polynomial fit 
        plateau_tol: plateau tolerance [nA]

    Outputs: [Vrf_final, Vdc_final] (array)

    After a Vdc is set, the algorithm will set Vrf from 0 to Vrf_params[0]
    Then Vrf is going to be swep  get a data range that is {scan_range}

    Errors: 
        -1: Sweeping outside allowed scan range
        -2: Not enough data points in a sweep to perform polyfit

    Recomendations:
        -   Try to keep poly_deg low if the scan_range is low to minimize error ie. polyfit poorly conditioned

    """ 
    # Still need to do error checking for variables

    print '\n','Running find_plateaus. Sweeeping Vdc ->', Vdc_params, '. Sweeping Vrf ->', Vrf_params

    # Turn on Rf component of Vrf
    RF_component()

    # Fix Vdc at Vdc_min
    Vdc = set_Vdc(Vdc_params[0])
    print 'Fixed Vdc =', Vdc

    iteration = 1
    length = (scan_range/inc) + 1

    if (scan_range/inc)+1 < poly_deg:
        # Current settings might not allow for a good polyfit
        print '________ERROR________'
        print 'Number of points in a sweep', (length), 'is less than the order of the polyfit',(poly_deg)
        exit()

    while True:

        # Set an intial Vrf 
        Vrf = set_Vrf(Vrf_params[0])   
        print '\n','--------- iteration ', iteration,' Vdc:', Vdc,' ---------\n'

        current_array = []
        n = 1
        I_n = n*(1.60217662e-19)*frequency                                          # Target current 

        while True:           

            current_array.append(get_current(Vrf,Vdc))                              # Build current_array
            if len(current_array) > length:                                         # Trim the array
                current_array.pop(0)
                #plot_current(Vrf-scan_range,Vrf,current_array)

                check_plateau(Vrf-scan_range,Vrf,current_array,poly_deg)

            #if np.isclose(I_n,current_array[round(len(current_array)/2)],0.01):     # Check if array is centered around target current
            #    found_plateau = check_plateau(Vrf-scan_range,Vrf,current_array)

            Vrf += inc
            if Vrf >= Vrf_params[1]:
                print 'Reached Vrf_max'
                break
        
        iteration += 1
        Vdc += inc
        if Vdc >= Vdc_params[1]:
            print 'Reached Vdc_max'
            break

    return

def check_plateau(start,end,current,poly_deg):
    # Fit polynomial and its derivatives
    x = np.linspace(start,end,len(current))
    y = np.array(current)
    p = np.poly1d(np.polyfit(x,y,poly_deg))                            
    p1 = np.polyder(p)   
    p2 = np.polyder(p1)
    error = sum(abs(p(x) - y))
    roots_p1 = np.roots(p1)
    roots_p2 = np.roots(p2)
    real_roots_p1 = [r.real for r in roots_p1 if np.isclose(r.imag, 0) and (start <= r.real <= end)]
    real_roots_p2 = [r.real for r in roots_p2 if np.isclose(r.imag, 0) and (start <= r.real <= end)]
    """
        Conditions to be met for X to classify as plateau:
        1. f''(X) == 0                                                      (or at least ~= 0 in the future?)
        2. | f'([X_left,X_right]) | <  epsilon
        3. | f([X_left,X_right]) | < plateau_tol                            # make sure this lines up roughly with integer value
        4. current around plateau is above min_current                      # At least one electron about ~0.9
    """
    plot_current(start,end,current,p,p1,real_roots_p1,p2,real_roots_p2)
    
    return

def plot_current(start,end,current,p=None,p1=None,p1_roots=None,p2=None,p2_roots=None):
    x = np.linspace(start,end,len(current))
    y = np.array(current)
    fig = plt.figure()
    fig.suptitle('Vrf ='+str([start,end]))
    plt.plot(x,y)
    if p:                                                       # Optionally plot the polyfit
        plt.plot(np.linspace(start,end,1000),p(np.linspace(start,end,1000)))
    if p1 and p1_roots:                                         # Optionally plot the 1st derivative
        plt.plot(p1_roots,p(p1_roots),'o', color='black')
    if p2 and p2_roots:                                         # Optionally plot the 1st derivative
        plt.plot(p2_roots,p(p2_roots),'x', color='red')
    for n in [1,2]:
        I_N = n*(1.60217662e-19)*frequency*1e9
        xx = np.linspace(start,end,1000)
        yy =  np.array(1000*[I_N])
        plt.plot(xx,yy)
    plt.show(block=False)
    plt.pause(2)
    return

Vrf_params = [0.63,0.7]
Vdc_params = [0.65,0.67]
scan_range = 0.02
frequency = 100e6
poly_deg = 5
plateau_tol = 0.02


plateaus = find_plateau(Vrf_params,Vdc_params,scan_range,frequency,poly_deg,plateau_tol)