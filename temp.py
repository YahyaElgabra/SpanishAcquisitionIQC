

    # Sweep Vrf and get current measurement
    iteration = 1
    while True:
        Vrf = set_Vrf(Vrf_params[0])
        print 'Initial Vrf =', Vrf
        while True:
             
            print '\n','--------- iteration ', iteration,' Vdc:', Vdc,' ---------\n'

            # Error checking
            # 1. Check if the sweep will scan outside the allowed Vrf range
            # 2. Check if the polyfit is good, ie. if the number 
            # 3. 

            

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


    

if plateaus:
    reduce_Vqpc(0.1)    # arbitrary value -> needs to be fixed
    print 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx NO PLATEAUS FOUND xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    break               # Exit the loop (only done for testing right now)

#print history

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

