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

def measure(Vdc,l,r):
    """
        This function returns an array of current values for a
        sweep of Vrf at a fixed Vdc

        Inputs: Vdc (float), l (float), r (float)
        Outputs: current_array (array)
    """
    current = []
    Vrf_array = np.linspace(l,r,((abs(l-r))/inc)+1)
    #print(Vrf_array)
    for i in Vrf_array:
        Vrf = set_Vrf(i)
        current.append(get_current(Vrf,Vdc))
    return np.asarray(current)

def find_plateau(Vrf_params,Vdc_params,scan_range,scan_increment,poly_deg,plateau_tol):

    """
    This funciton finds the plateau in the current by looking at polynomial derivatives

    Inputs: Vrf_params (array), Vdc_params (array), scan_range (float), scan_increment (float), poly_deg (int), plateau_tol (float)
        Vrf_params = [Vrf_start,Vrf_end] (float) [V]
        Vdc_params = [Vdc_start,Vdc_end] (float) [V]
        scan_range: range of scan to find plateau [V]
        scan_increment: increment of scan to find plateau [V]
        poly_deg: degree of polynomial fit 
        plateau_tol: plateau tolerance [nA]

    Outputs: [Vrf_final, Vdc_final] (array)

    Errors: 
        -1: Sweeping outside allowed scan range
        -2: Not enough data points in a sweep to perform polyfit

    Recomendations:
        -   Try to keep poly_deg low if the scan_range is low to minimize error ie. polyfit poorly conditioned

    """ 
    # Still need to do error checking for variables

    print '\n','Running find_plateaus at Vdc = ', Vdc_params[0] , ' Sweeping Vrf -> ', Vrf_params

    # Turn on Rf component of Vrf

    # Fix Vdc
    Vdc = set_Vdc(Vdc_params[0])
    print 'Fixed Vdc =', Vdc

    # Set an intial Vrf 
   

    print '\n', 'Starting sweep ...'

    # Sweep Vrf and get current measurement
    iteration = 0
    while True:
        Vrf = set_Vrf(Vrf_params[0])
        print 'Initial Vrf =', Vrf
        while True:
             
            print '\n','--------- iteration ', iteration,' Vdc:', Vdc,' ---------\n'

            if Vrf+scan_range > Vrf_params[1]:
                # Vrf is potentially outside allowed scan range
                print '________ERROR________'
                print 'Sweeping outside allowed scan range, last Vrf = ', Vrf, ' scan_range = ', scan_range
                break
            if (scan_range/inc)+1 < poly_deg:
                # Current settings might not allow for a good polyfit
                print '________ERROR________'
                print 'Number of points in a sweep', ((scan_range/inc)+1), 'is less than the order of the polyfit',(poly_deg)
                return -2

            # Measure current
            
            x = np.linspace(Vrf,Vrf+scan_range,(scan_range/inc)+1)
            print 'Scanning from Vrf =', x[0],'to',round(x[len(x)-1],3)
            y = measure(Vdc,Vrf,Vrf+scan_range)
            print 'Measuring current ranging from I =',min(y),'nA to',max(y)

            # Fit polynomial and its derivatives
            p = np.poly1d(np.polyfit(x,y,poly_deg))                            
            p1 = np.polyder(p)                          
            p2 = np.polyder(p1)
            error = sum(abs(p(x) - y))
            print 'Fit error: ', error
            
            # Find the roots of the first and second derivatives that are in the 
            roots_p1 = np.roots(p1)
            roots_p2 = np.roots(p2)
            real_roots_p1 = [r.real for r in roots_p1 if np.isclose(r.imag, 0) and (Vrf <= r.real <= Vrf+scan_range)]
            real_roots_p2 = [r.real for r in roots_p2 if np.isclose(r.imag, 0) and (Vrf <= r.real <= Vrf+scan_range)]

            # Check if the points of inflection can classify as plateaus
            """
                Conditions to be met for X to classify as plateau:
                1. f''(X) == 0          (or at least ~= 0 in the future?)
                2. | f'([X_left,X_right]) | <  epsilon
                3. | f([X_left,X_right]) | < plateau_tol                            # make sure this lines up roughly with integer value
                4. current around plateau is above min_current                      # At least one electron about ~0.9
            """
            epsilon = 0.1              # [nA/V]
            min_current = 0.2       
            plateaus = []
            print 'Evaluating points of inflection...' , real_roots_p2
            
            for i in real_roots_p2:
                
                # Also find the width of the plateau

                # Evaluate neighborhood around root
                Vrf_left = i-(inc*2)
                Vrf_right = i+(inc*2)
                if Vrf_left < Vrf or Vrf_right > Vrf+scan_range:                                           # Need tighter conditions for dict
                    # Current value might not be good for the fit or if it is too low
                    print 'WARNING: root',i,' might be too close to edge of fit as range:',np.round([Vrf_left,Vrf_right],4),'... adjusting range'
                    Vrf_left = Vrf if Vrf_left < Vrf else Vrf_left
                    Vrf_right = Vrf+scan_range if Vrf_right > Vrf+scan_range else Vrf_right
                x_array = np.linspace(Vrf_left,Vrf_right,50)
            
                # Check the four conditions
                potential_Vrf = round(i,3) if round(i*1000)%2 == 0 else round(i,3)+0.001
                potential_current = get_current(potential_Vrf,Vdc)
                cond1 = p2(i) < 0.01                                                        # d2_tol is arbitrary right now
                cond2 = False not in (p1(x_array) < 50)                                     # d1_tol = 0.100 nA / 0.002 V
                cond3 = False not in (abs(p(x_array)-potential_current) < plateau_tol)
                cond4 = False not in (p(x_array) > min_current)
                print 'Evaluating',i,'with conditions:',cond1,cond2,cond3,cond4

                # Write error messages for conditions later
                if cond1 and cond2 and cond3 and cond4:                                                             
                    print '-------> Found plateau at (Vrf,Vdc)=',(potential_Vrf,Vdc),'with a current of',potential_current
                    plateaus.append([potential_Vrf,Vdc])         
    
            #print 'Vertices at:',real_roots_p1
            #print 'Points of inflection at',real_roots_p2
            
            # To show the results of the fit 
            new_x = np.linspace(Vrf,Vrf+scan_range,1000)
            new_y = p(new_x)
            p1_x = real_roots_p1
            p1_y = p(p1_x)
            p2_x = real_roots_p2
            p2_y = p(p2_x)

            fig = plt.figure()
            fig.suptitle('Iteration '+ str(iteration))
            plt.plot(x,y)
            plt.plot(new_x,new_y)
            plt.plot(p1_x, p1_y, 'o', color='black')
            plt.plot(p2_x, p2_y, 'x', color='red')
            plt.plot(x_array,p(x_array),color='black',linestyle='dotted')
            plt.show(block=True)
            #plt.pause(5)

            Vrf = round(scan_increment+Vrf,3)
            iteration += 1

        iteration += 1
        if Vdc == Vdc_params[1]:
            break
        Vdc = round(Vdc+inc,3)
    print '\n','Final plateaus found:',plateaus
    return plateaus

def sweep_algorithm():
    """
        Wrapper function for find plateaus, arguments the same as find_plateaus, also does some post-processing

        Inputs: Vrf_params (array), Vdc_params (array), scan_range (float), scan_increment (float), poly_deg (int), plateau_tol (float)

        Outputs: 
    """

    return

Vdc_params = [0.64,0.67]
Vrf_params = [0.63,0.7]
scan_range = 0.02
scan_increment = 0.01
poly_deg = 6
plateau_tol = 0.02




plateaus = find_plateau(Vrf_params,Vdc_params,scan_range,scan_increment,poly_deg,plateau_tol)

if plateaus:
    reduce_Vqpc(0.1)    # arbitrary value -> needs to be fixed
    print 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx NO PLATEAUS FOUND xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    break               # Exit the loop (only done for testing right now)

print history

# Don't pass 1nA of current
# To avoid bsuting device

# Don't look for anything  I/(e*f) = n

















# Check that the values of the dictionaries are all there

#Vdc = 0.63
#for i in range(50):
#    Vrf = 0.63
#    for j in range(50):
#        print(current_dict[str(Vrf),str(Vdc)])
#        Vrf += inc
#    Vdc += inc
#print(Vrf,Vdc)     

# Print all of the key value pairs from dictionary

#for key, value in current_dict.items():
#    print key,' : ', value 


#######################################
# OLD FUNCTIONS

def min_right(i,tau):
    """
        This function finds the current interval for which 
        Inputs: i_limit (float), tau (float)
    """
    #for i in range()

def min_left():
    return

def max_right():
    return

def max_left():
    return

def find_left_plateau():
    """
        Inputs: T (np.array), tau (float)


    """
    return



