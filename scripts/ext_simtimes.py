#!/usr/bin/python

import os
import re
import sys
import shutil
import math

#row = #numSchedQs; #col = #threadsPERschedq
rootConfig = []
#sync = [ ["AtomicLock", "Mutex"], ["AtomicLock"], ["AtomicLock", "Mutex"] ]
sync = [ ["AtomicLock"], ["AtomicLock"], ["AtomicLock"] ]
rtmretries = [ ["NAretry"], ["NAretry"], [] ]
threads = []
maxSchedQs = 0
schedQs = []
simtime_avg = [] 
simtime_std = [] 
trial_buf = []
allresults_avg = []
allresults_std = []
simruntime = 0

def usage():
    print "ext_simtimes.py /path/to/log-<model> <MultiSet|SplayTree> <t value based on confidence level>"
    sys.exit()

def myprint(src, string):
#    print string
    src.write(string + "\n")

if len(sys.argv) != 4:
    usage()
else:
    logconfig = sys.argv[1]
    datastruct = sys.argv[2]
    tval = float(sys.argv[3])

#extract root directory and model name
#ret = re.search("(^.+/?)log-(.+?)$", logconfig)
ret = re.search("(^.+/?)log-(.+?)-(.+?)$", logconfig)
basedir = ret.group(1)
model = ret.group(2)
migration = ret.group(3)

#determine how many syncConfigs there are
os.system("cd " + basedir + " && ls " + logconfig + "-*." + datastruct + " > syncConfigs.tmp")
src = open(basedir + "syncConfigs.tmp")
for line in src:
    ret = re.search(".*log-"+model+"-.*mig-([a-zA-Z]+)-", line)
    if ret.group(1) not in rootConfig:
#        rtmretries.append([])
        rootConfig.append(ret.group(1))
#        if ret.group(1) != "TSXRTM":
#            rtmretries[-1].append("NAretry")
src.close()
os.remove(basedir + "syncConfigs.tmp")

#determine how many different TSX confis there are for RTM if any
rtmRetryCount = []
os.system("cd " + basedir + " && ls " + logconfig + "-TSXRTM-* > tsxconfigs.tmp")
src = open(basedir + "tsxconfigs.tmp")
for line in src:
    ret = re.search(".*log-.*-.*mig-TSXRTM-([0-9]+)retry", line)
    if int(ret.group(1)) not in rtmRetryCount:
        rtmRetryCount.append(int(ret.group(1)))

rtmRetryCount.sort()

for irtm in range(len(rtmRetryCount)): 
    rtmretries[rootConfig.index("TSXRTM")].append(str(rtmRetryCount[irtm])+"retry")

#    ret = re.search(".*log-.*-TSXRTM-([0-9]+retry)", line)
#    if ret.group(1) not in rtmretries[rootConfig.index("TSXRTM")]:
#        rtmretries[rootConfig.index("TSXRTM")].append(ret.group(1))
#        if ret.group(1) != "NAretry":
#            ret2 = re.search("([0-9]+)retry", ret.group(1))
src.close()
os.remove(basedir + "tsxconfigs.tmp")

#get root directory
ret = re.search("(^.+/?)log-(.+?)$", logconfig)
basedir = ret.group(1)
model = ret.group(2)

print rootConfig
print rtmretries
threadsPERschedq = [ [], [], [], [], [], [], [] ]
schedqPERthreads = [ [], [], [], [], [], [], [] ]
for iroot in range(len(rootConfig)):
    simtime_avg.append([]);
    simtime_std.append([]);
    for isync in range(len(sync[iroot])):
        simtime_avg[iroot].append([]);
        simtime_std[iroot].append([]);
        for iretry in range(len(rtmretries[iroot])):
            simtime_avg[iroot][isync].append([]);
            simtime_std[iroot][isync].append([]);
        
            #add 7 potential schedqs and 7 threads to matrix
            for i in range(7):
                simtime_avg[iroot][isync][iretry].append([])
                simtime_std[iroot][isync][iretry].append([])
                for i2 in range(7):
                    simtime_avg[iroot][isync][iretry][i].append([])
                    simtime_std[iroot][isync][iretry][i].append([])

            target = basedir+"simtimes-"+model+"-"+rootConfig[iroot]+"-"+rtmretries[iroot][iretry]+"-"+sync[iroot][isync] + "-" + datastruct.lower()
            cmd = "cd "+basedir+" && grep \"Simulation complete\" "+logconfig+ "-"+rootConfig[iroot]+"-"+rtmretries[iroot][iretry]+"-"+sync[iroot][isync]+"-*."+datastruct+" > "+target
            #print "Computing results for " + target

            os.system(cmd)
            shutil.move(target, target + '.tmp')
            src = open(target + '.tmp')
            dst = open(target + '.txt', "wb")
            #determine current syncmechanism being parsed
            i2 = 1
            for line in src:
                #config changes every 10 lines 
                ret = re.search(".*log-.*threads-(\d)", line)
                if int(ret.group(1)) == 0:
                    #determine new configuration
                    ret = re.search(".*log-.*-(\d+)schedQs-(\d)threads-.*", line)

                    numsc = int(ret.group(1))
                    numthrs = int(ret.group(2))

                    try:
                        ind = threadsPERschedq[numsc-1][0]
                    except IndexError:
                        while len(threadsPERschedq) < numsc:
                            threadsPERschedq.append([])

                    try:
                        ind = simtime_avg[iroot][isync][iretry][numsc-1]
                    except IndexError:
                        while len(simtime_avg[iroot][isync][iretry]) < numsc:
                            simtime_avg[iroot][isync][iretry].append([])
                            simtime_std[iroot][isync][iretry].append([])

                    if numthrs not in threadsPERschedq[numsc-1]:
                        threadsPERschedq[numsc-1].append(numthrs)
                    if numsc not in schedqPERthreads[numthrs-1]:
                        schedqPERthreads[numthrs-1].append(numsc)

                    delta = len(threadsPERschedq[numsc-1]) - len(simtime_avg[iroot][isync][iretry][numsc-1])
                    if delta != 0:
                        for i in range(delta):
                            simtime_avg[iroot][isync][iretry][numsc-1].append([])
                            simtime_std[iroot][isync][iretry][numsc-1].append([])

                    dst.write("**********************************\n")
                    dst.write("* " + str(numthrs) + " Threads - " + str(numsc) + " Schedule Queue(s)\n")
                    dst.write("**********************************\n")

                #extract simtimes
                ret = re.findall(r"\d+\.\d+", line)
                if not ret:
                    ret = re.findall(r"\d+", line)
                time = float(ret[0])
                dst.write( str(time) + "\n")
                simruntime += time
                trial_buf.append(time)

                #dont calculate stats until 10 lines have been parsed
                if i2 % 10 == 0:
                    time_varsum = 0
                    thrind = threadsPERschedq[numsc-1].index(numthrs) 
                    #print "avg_runtime for "+rootConfig[iroot]+","+sync[iroot][isync]+","+rtmretries[iroot][iretry]+","+str(numsc)+"schedQs,"+str(numthrs)+"threads = "+str(simruntime/10)
                    simtime_avg[iroot][isync][iretry][numsc-1][thrind] = str(simruntime/10)

                    #calculate simtime_std
                    for i3 in range(10):
                        time_varsum += pow((trial_buf[i3] - (simruntime/10)), 2)
                    simtime_std[iroot][isync][iretry][numsc-1][thrind] = str(math.sqrt(time_varsum/10))
                    del trial_buf[:]
                    simruntime = 0 

                i2 += 1

            del threads[:]
            del schedQs[:]
            
            src.close()
            dst.close()
            os.system("rm *.tmp")

#print results
#for each locking mechanism, for each schedQ, for each thread, for each config
#syncMechs = ["Atomic", "Mutex"]
syncMechs = [ "Atomic" ]
datastruct = datastruct.lower()
src = open(basedir + model + "-timeVSthreads-" + datastruct + ".txt", "wb")
for pisync in range(len(syncMechs)):
    myprint(src, "# Simulation runtime summary for " + model + " using " + syncMechs[pisync])

    for pisc in range(len(threadsPERschedq)):
        if not threadsPERschedq[pisc]:
            continue

        myprint(src, "# " + str(pisc+1) + " Schedule Queue(s) per X Worker Threads") 

        #create header
        hdr = "# "
        if "NOTSX" in rootConfig:
            hdr +=  "NOTSX      ERRNOTSX   "

        if "TSXHLE" in rootConfig:
            if syncMechs[pisync] == "Atomic":
                hdr +=   "TSXHLE     ERRTSXHLE  "

            if "TSXRTM" in rootConfig:
                for i in range(len(rtmretries[rootConfig.index("TSXRTM")])):
                    hdr += "TSXRTM" + str(i).ljust(5) + "ERRTSXRTM" + str(i) + " "     

        myprint(src, hdr)
        for pithr in range(len(threadsPERschedq[pisc])):
            results = str(threadsPERschedq[pisc][pithr])
            for piroot in range(len(rootConfig)):
                if not (syncMechs[pisync] == "Mutex" and rootConfig[piroot] == "TSXHLE"):
                    if rootConfig[piroot] == "TSXRTM":
                        for piretry in range(len(rtmretries[rootConfig.index("TSXRTM")])):
                            error = tval *(float(simtime_std[piroot][pisync][piretry][pisc][pithr])/math.sqrt(10))
                            results += " " + str(round(float(simtime_avg[piroot][pisync][piretry][pisc][pithr]), 9)).ljust(10) + " " + str(round(error, 6)).ljust(10)
                    else:
                        error = tval *(float(simtime_std[piroot][pisync][0][pisc][pithr])/math.sqrt(10))
                        results += " " + str(round(float(simtime_avg[piroot][pisync][0][pisc][pithr]), 9)).ljust(10) + " " + str(round(error, 6)).ljust(10)

            myprint(src, results)
src.close()

#for each locking mechanism, for each thread, for each schedQ, for each config
src = open(basedir + model + "-timeVSschedQs-" + datastruct + ".txt", "wb")
for pisync in range(len(syncMechs)):
    myprint(src, "# Simulation runtime summary for " + model + " using " + syncMechs[pisync])

    for pithr in range(len(schedqPERthreads)):
        myprint(src, "# " + str(pithr+1) + " Worker Threads per X Schedule Queues") 

        #create header
        hdr = "# "
        if "NOTSX" in rootConfig:
            hdr +=  "NOTSX      ERRNOTSX   "

        if "TSXHLE" in rootConfig:
            if syncMechs[pisync] == "Atomic":
                hdr +=   "TSXHLE     ERRTSXHLE  "

            if "TSXRTM" in rootConfig:
                for i in range(len(rtmretries[rootConfig.index("TSXRTM")])):
                    hdr += "TSXRTM" + str(i).ljust(5) + "ERRTSXRTM" + str(i) + " "     

        myprint(src, hdr)
        for pisc in schedqPERthreads[pithr]:
            results = str(pisc)
            for piroot in range(len(rootConfig)):
                thrind = threadsPERschedq[pisc-1].index(pithr+1)
                if not (syncMechs[pisync] == "Mutex" and rootConfig[piroot] == "TSXHLE"):
                    if rootConfig[piroot] == "TSXRTM":
                        for piretry in range(len(rtmretries[rootConfig.index("TSXRTM")])):
                            error = tval *(float(simtime_std[piroot][pisync][piretry][pisc-1][thrind])/math.sqrt(10))
                            results += " " + str(round(float(simtime_avg[piroot][pisync][piretry][pisc-1][thrind]), 9)).ljust(10) + " " + str(round(error, 6)).ljust(10)
                    else:
                        error = tval *(float(simtime_std[piroot][pisync][0][pisc-1][thrind])/math.sqrt(10))
                        results += " " + str(round(float(simtime_avg[piroot][pisync][0][pisc-1][thrind]), 9)).ljust(10) + " " + str(round(error, 6)).ljust(10)

            myprint(src, results)
src.close()
