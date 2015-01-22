#!/usr/bin/python

import os
import re
import sys
import shutil
import math

threads_1sc = []
threads_2sc = []
trial_buf = []
notsx_1sc_avg = []
notsx_2sc_avg = []
notsx_1sc_std = []
notsx_2sc_std = []
tsx_1sc_avg = [[]]
tsx_2sc_avg = [[]]
tsx_1sc_std = [[]]
tsx_2sc_std = [[]]
simruntime = 0

def usage():
    print "ext_simtimes /path/to/log-<model1> <t value based on confidence level>"

if len(sys.argv) != 3:
    usage()
    sys.exit()
else:
    logconfig = sys.argv[1]
    tval = sys.argv[2] 

# parse NOTSX logs
ret = re.search("(^.+/?)log-(.+?)$", logconfig) 
basedir = ret.group(1)
target = basedir + "simtimes-" + ret.group(2) + "-NOTSX" 
os.system("cd " + ret.group(1) + " && grep \"Simulation complete\" " + logconfig + "-NOTSX-* > " + target) 
shutil.move(target, target + '.tmp')
src = open(target + '.tmp')
dest = open(target + '.txt', "wb")
i = 1  
for line in src:
    #config changes ever 10 lines
    if (i-1) % 10 == 0:
        # determine new configuration
        ret = re.search(".*log-.*-NOTSX-([0-9]?)schedQs-([0-9]?)threads-.*", line)
        
        numsc = int(ret.group(1))
        numthrs = int(ret.group(2))
        
        dest.write("********************************\n")
        dest.write("* " + str(numthrs) + " Threads - " + str(numsc) + " Schedule Queue(s)\n")
        dest.write("********************************\n")

    ret1 = re.findall(r"\d+.\d+e[-+]?\d+", line)
    if ret1:
        dest.write(ret1[0] + "\n")
        simruntime += float(ret1[0])
        trial_buf.append(float(ret1[0]))
    else:
        ret1 = re.findall(r"\d+.\d+", line)
        dest.write(ret1[0] + "\n")
        simruntime += float(ret1[0])
        trial_buf.append(float(ret1[0]))

    # dont store until it's parsed 10 lines
    if i % 10 == 0:
        varsum = 0
        if numsc == 1:
#            notsx_1sc_avg.append(round(simruntime/10, 5))
            notsx_1sc_avg.append(simruntime/10)
            threads_1sc.append(numthrs)
            #calculate std dev
            for i2 in range(10):
                varsum += pow((trial_buf[i2] - (simruntime/10)), 2)
            notsx_1sc_std.append(round(math.sqrt(varsum/10), 13))
            varsum = 0
            del trial_buf[:]
        elif numsc == 2:
#            notsx_2sc_avg.append(round(simruntime/10, 5))
            notsx_2sc_avg.append(simruntime/10)
            threads_2sc.append(numthrs)
            #calculate std dev
            for i2 in range(10):
                varsum += pow((trial_buf[i2] - (simruntime/10)), 2)
            notsx_2sc_std.append(round(math.sqrt(varsum/10), 13))
            varsum = 0
            del trial_buf[:]
        simruntime = 0
        
    i += 1

src.close()
dest.close()
os.remove(target + '.tmp')

# parse TSX logs
#retries = [2, 4, 6, 8, 10]
retries = [ 10, 100, 1000, 10000 ]
ret = re.search("(^.+/?)log-(.+?)$", logconfig) 
model = ret.group(2)
for i1 in range(len(retries)):
    tsx_1sc_avg.append([])
    tsx_2sc_avg.append([])
    tsx_1sc_std.append([])
    tsx_2sc_std.append([])
    target = basedir + "simtimes-" + model + "-TSX-" + str(retries[i1]) 
    os.system("cd " + basedir + " && grep \"Simulation complete\" " + logconfig + "-TSX-" + str(retries[i1]) + "retry-* > " + target) 
    shutil.move(target, target + '.tmp')
    src = open(target + '.tmp')
    dest = open(target + '.txt', "wb")
    i = 1  
    for line in src:
        #config changes ever 10 lines
        if (i-1) % 10 == 0:
            # determine new configuration
            ret = re.search(".*log-.*-TSX-[0-9]+retry-([0-9]?)schedQs-([0-9]?)threads-.*", line)
            
            numsc = int(ret.group(1))
            numthrs = int(ret.group(2))
            
            dest.write("********************************\n")
            dest.write("* " + str(numthrs) + " Threads - " + str(numsc) + " Schedule Queue(s)\n")
            dest.write("********************************\n")

        ret1 = re.findall(r"\d+.\d+e[-+]?\d+", line)
        if ret1:
            dest.write(ret1[0] + "\n")
            simruntime += float(ret1[0])
            trial_buf.append(float(ret1[0]))
        else:
            ret1 = re.findall(r"\d+.\d+", line)
            dest.write(ret1[0] + "\n")
            simruntime += float(ret1[0])
            trial_buf.append(float(ret1[0]))

        # dont store until it's parsed 10 lines
        if i % 10 == 0:
            if numsc == 1:
#                tsx_1sc_avg[i1].append(round(simruntime/10, 5))
                tsx_1sc_avg[i1].append(simruntime/10)
                threads_1sc.append(numthrs)
                #calculate std dev
                for i2 in range(10):
                    varsum += pow((trial_buf[i2] - (simruntime/10)), 2)
                tsx_1sc_std[i1].append(round(math.sqrt(varsum/10), 13))
                varsum = 0
                del trial_buf[:]
            elif numsc == 2:
#                tsx_2sc_avg[i1].append(round(simruntime/10, 5))
                tsx_2sc_avg[i1].append(simruntime/10)
                threads_2sc.append(numthrs)
                #calculate std dev
                for i2 in range(10):
                    varsum += pow((trial_buf[i2] - (simruntime/10)), 2)
                tsx_2sc_std[i1].append(round(math.sqrt(varsum/10), 13))
                varsum = 0
                del trial_buf[:]
            simruntime = 0
            
        i += 1

    src.close()
    dest.close()
    os.remove(target + '.tmp')

#print and log out summary of simruntimes
summary = open(basedir + "summary-"+model, "wb")
print "# Simulation Runtime Summary for 1 Schedule Queue"
summary.write("# Simulation Runtime Summary for 1 Schedule Queue\n")
hdr = '#\tNOTSX\t\t\tERRNOTSX'
summary.write(hdr)
for i in range(len(retries)):
    hdr += '\t\tTSX'+str(retries[i]) + '\t\tERR' + str(retries[i])
    summary.write('\t\tTSX' + str(retries[i]) + '\t\t\tERRTSX' + str(retries[i]) + "\t")
summary.write('\n')
print hdr
for i in range(len(notsx_1sc_avg)):
    error = "\t" + str(round(float(tval) * (notsx_1sc_std[i]/math.sqrt(10)), 13)).ljust(13) 
    results = str(threads_1sc[i]) + "\t" + str(notsx_1sc_avg[i]).ljust(13) + error
    for i2 in range(len(retries)):
        results += "\t" + str(tsx_1sc_avg[i2][i]).ljust(13) + "\t" + str(round(float(tval) * (tsx_1sc_std[i2][i]/math.sqrt(10)), 13)).ljust(13)
    print results
    summary.write(results + "\n")

print "# Simulation Runtime Summary for 2 Schedule Queue"
summary.write("# Simulation Runtime Summary for 2 Schedule Queue\n")
hdr = '#\tNOTSX\t\t\tERRNOTSX'
summary.write(hdr)
for i in range(len(retries)):
    hdr += '\t\tTSX'+str(retries[i]) + '\t\tERR' + str(retries[i])
    summary.write('\t\tTSX' + str(retries[i]) + '\t\t\tERRTSX' + str(retries[i]) +"\t")
summary.write('\n')
print hdr
for i in range(len(notsx_2sc_avg)):
    error = "\t" + str(round(float(tval) * (notsx_2sc_std[i]/math.sqrt(10)), 13)).ljust(13) 
    results = str(threads_2sc[i]) + "\t" + str(notsx_2sc_avg[i]).ljust(13) + error
    for i2 in range(len(retries)):
        results += "\t" + str(tsx_2sc_avg[i2][i]).ljust(13) + "\t" + str(round(float(tval) * (tsx_2sc_std[i2][i]/math.sqrt(10)), 13)).ljust(13)
    print results
    summary.write(results + "\n")

print "# Simulation StdDev Summary for 1 Schedule Queue"
summary.write("# Simulation Stddev Summary for 1 Schedule Queue\n")
hdr = '#\tNOTSX'
summary.write(hdr)
for i in range(len(retries)):
    hdr += '\t\tTSX'+str(retries[i])
    summary.write('\t\t\tTSX' + str(retries[i]))
summary.write('\n')
print hdr
for i in range(len(notsx_1sc_std)):
    results = str(threads_1sc[i]) + "\t" + str(notsx_1sc_std[i]).ljust(13)
    for i2 in range(len(retries)):
        results += "\t" + str(tsx_1sc_std[i2][i]).ljust(13)
    print results
    summary.write(results + "\n")

print "# Simulation StdDevSummary for 2 Schedule Queue"
summary.write("# Simulation StdDev Summary for 2 Schedule Queue\n")
hdr = '#\tNOTSX'
summary.write(hdr)
for i in range(len(retries)):
    hdr += '\t\tTSX'+str(retries[i])
    summary.write('\t\t\tTSX' + str(retries[i]))
summary.write('\n')
print hdr
for i in range(len(notsx_2sc_std)):
    results = str(threads_2sc[i]) + "\t" + str(notsx_2sc_std[i]).ljust(13)
    for i2 in range(len(retries)):
        results += "\t" + str(tsx_2sc_std[i2][i]).ljust(13) 
    print results
    summary.write(results + "\n")
