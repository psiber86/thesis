#!/usr/bin/python

import os
import re
import sys
import shutil
import math

#row = #numSchedQs; #col = #threadsPERschedq
rootConfig = []
#sync = [ ["AtomicLock", "Mutex"], ["AtomicLock"], ["AtomicLock", "Mutex"] ]
sync = [ ["AtomicLock"], ["AtomicLock"], ["AtomicLock"] , ["AtomicLock"]]
rtmretries = [ ["NAretry"], ["NAretry"], [], []]
threads = []
maxSchedQs = 0
schedQs = []
simtime_avg = [] 
simtime_std = [] 
simtime_stderr = []
trial_buf = []
allresults_avg = []
allresults_std = []
simruntime = 0
# for 95% confidence
tval = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228]

def usage():
    print "ext_simtimes.py /path/to/log-<model> <MultiSet|SplayTree|LinkedList>"
    sys.exit()

def myprint(src, string):
#    print string
    src.write(string + "\n")

if len(sys.argv) != 3:
    usage()
else:
    logconfig = sys.argv[1]
    datastruct = sys.argv[2]

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

#determine how many different TSX confis there are for each RTM if any
rtmconfig = ["TSXRTM", "TSXRTMSTRICT"]
for irtm in range(len(rtmconfig)):
    rtmRetryCount = []
    os.system("cd " + basedir + " && ls " + logconfig + "-"+rtmconfig[irtm]+"-* > tsxconfigs.tmp")
    src = open(basedir + "tsxconfigs.tmp")
    for line in src:
        ret = re.search(".*log-.*-.*mig-"+rtmconfig[irtm]+"-([0-9]+)retry", line)
        if int(ret.group(1)) not in rtmRetryCount:
            rtmRetryCount.append(int(ret.group(1)))

    rtmRetryCount.sort()
    for iretry in range(len(rtmRetryCount)): 
        rtmretries[rootConfig.index(rtmconfig[irtm])].append(str(rtmRetryCount[iretry])+"retry")

#    ret = re.search(".*log-.*-TSXRTM-([0-9]+retry)", line)
#    if ret.group(1) not in rtmretries[rootConfig.index("TSXRTM")]:
#        rtmretries[rootConfig.index("TSXRTM")].append(ret.group(1))
#        if ret.group(1) != "NAretry":
#            ret2 = re.search("([0-9]+)retry", ret.group(1))
src.close()
os.remove(basedir + "tsxconfigs.tmp")

##get root directory
#ret = re.search("(^.+/?)log-(.+?)$", logconfig)
#basedir = ret.group(1)
#model = ret.group(2)

print rootConfig
print rtmretries
threadsPERschedq = [ [], [], [], [], [], [], [] ]
schedqPERthreads = [ [], [], [], [], [], [], [] ]
for iroot in range(len(rootConfig)):
    simtime_avg.append([]);
    simtime_std.append([]);
    simtime_stderr.append([]);
    for isync in range(len(sync[iroot])):
        simtime_avg[iroot].append([]);
        simtime_std[iroot].append([]);
        simtime_stderr[iroot].append([]);
        for iretry in range(len(rtmretries[iroot])):
            simtime_avg[iroot][isync].append([]);
            simtime_std[iroot][isync].append([]);
            simtime_stderr[iroot][isync].append([]);
       
            #add 7 potential schedqs and 7 threads to matrix
            for i in range(7):
                simtime_avg[iroot][isync][iretry].append([])
                simtime_std[iroot][isync][iretry].append([])
                simtime_stderr[iroot][isync][iretry].append([])
                for i2 in range(7):
                    simtime_avg[iroot][isync][iretry][i].append([])
                    simtime_std[iroot][isync][iretry][i].append([])
                    simtime_stderr[iroot][isync][iretry][i].append([])

            target = basedir+"simtimes-"+model+"-"+rootConfig[iroot]+"-"+rtmretries[iroot][iretry]+"-"+sync[iroot][isync] + "-" + datastruct.lower()
            cmd = "cd "+basedir+" && grep \"Simulation complete\" "+logconfig+ "-"+rootConfig[iroot]+"-"+rtmretries[iroot][iretry]+"-"+sync[iroot][isync]+"-*."+datastruct+" > "+target
            #print "Computing results for " + target

            os.system(cmd)
            shutil.move(target, target + '.tmp')
            src = open(target + '.tmp')
            dst = open(target + '.txt', "wb")
            #determine current syncmechanism being parsed
            numTrials = 0
            numsc = 0
            numthrs = 0
            simrumtime = 0
            for line in src:
                #parse config
                ret = re.search(".*log-.*-(\d+)schedQs-(\d)threads-(\d)", line)
                if (int(ret.group(1)) != numsc) or (int(ret.group(2)) != numthrs) or (int(ret.group(3)) == 0):
                    # we have a new config, we should do the calculations for the old one now
                    # only if this isn't the first run
                    if simruntime > 0:
                        if numTrials < 10:
                            print "**********************"
                            print "WARNING: config only ran " + str(numTrials) + " trials"
                            print "     target = " + rootConfig[iroot]+"-"+rtmretries[iroot][iretry]+"-"+sync[iroot][isync]+"-"+str(numsc)+"schedQs-"+str(numthrs)+"threads-"+datastruct
                            print "**********************"

                        time_varsum = 0
                        thrind = threadsPERschedq[numsc-1].index(numthrs) 
                        #print "avg_runtime for "+rootConfig[iroot]+","+sync[iroot][isync]+","+rtmretries[iroot][iretry]+","+str(numsc)+"schedQs,"+str(numthrs)+"threads = "+str(simruntime/numTrials)
                        simtime_avg[iroot][isync][iretry][numsc-1][thrind] = str(simruntime/numTrials)

                        #calculate simtime_std
                        for i3 in range(numTrials):
                            time_varsum += pow((trial_buf[i3] - (simruntime/numTrials)), 2)
                        simtime_std[iroot][isync][iretry][numsc-1][thrind] = str(math.sqrt(time_varsum/numTrials))
                        simtime_stderr[iroot][isync][iretry][numsc-1][thrind] = float(simtime_std[iroot][isync][iretry][numsc-1][thrind])/math.sqrt(numTrials) * tval[numTrials-1]
                        del trial_buf[:]
                        simruntime = 0 

                    # clear number of trails for new config
                    numTrials = 0
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
                            simtime_stderr[iroot][isync][iretry].append([])

                    if numthrs not in threadsPERschedq[numsc-1]:
                        threadsPERschedq[numsc-1].append(numthrs)
                    if numsc not in schedqPERthreads[numthrs-1]:
                        schedqPERthreads[numthrs-1].append(numsc)

                    delta = len(threadsPERschedq[numsc-1]) - len(simtime_avg[iroot][isync][iretry][numsc-1])
                    if delta != 0:
                        for i in range(delta):
                            simtime_avg[iroot][isync][iretry][numsc-1].append([])
                            simtime_std[iroot][isync][iretry][numsc-1].append([])
                            simtime_stderr[iroot][isync][iretry][numsc-1].append([])

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
                numTrials += 1 

                #dont calculate stats until config changes have been parsed
                #if i2 % 10 == 0:
#                if finishedWithConfig == True:
#                    if numTrials < 10:
#                        print "**********************"
#                        print "WARNING: config only ran " + str(numTrials) + " trials"
#                        print "     target = " + rootConfig[iroot]+"-"+rtmretries[iroot][iretry]+"-"+sync[iroot][isync]+"-"+str(numsc)+"schedQs-"+str(numthrs)+"threads-"+datastruct
#                        print "**********************"
#
#                    time_varsum = 0
#                    thrind = threadsPERschedq[numsc-1].index(numthrs) 
#                    #print "avg_runtime for "+rootConfig[iroot]+","+sync[iroot][isync]+","+rtmretries[iroot][iretry]+","+str(numsc)+"schedQs,"+str(numthrs)+"threads = "+str(simruntime/numTrials)
#                    simtime_avg[iroot][isync][iretry][numsc-1][thrind] = str(simruntime/numTrials)
#
#                    #calculate simtime_std
#                    for i3 in range(numTrials):
#                        time_varsum += pow((trial_buf[i3] - (simruntime/numTrials)), 2)
#                    simtime_std[iroot][isync][iretry][numsc-1][thrind] = str(math.sqrt(time_varsum/numTrials))
#                    simtime_stderr[iroot][isync][iretry][numsc-1][thrind] = float(simtime_std[iroot][isync][iretry][numsc-1][thrind])/math.sqrt(numTrials) * tval[numTrials-1]
#                    del trial_buf[:]
#                    simruntime = 0 

            # do one more stats calculation for the last config
            if simruntime > 0:
                if numTrials < 10:
                    print "**********************"
                    print "WARNING: config only ran " + str(numTrials) + " trials"
                    print "     target = " + rootConfig[iroot]+"-"+rtmretries[iroot][iretry]+"-"+sync[iroot][isync]+"-"+str(numsc)+"schedQs-"+str(numthrs)+"threads-"+datastruct
                    print "**********************"

                time_varsum = 0
                thrind = threadsPERschedq[numsc-1].index(numthrs) 
                #print "avg_runtime for "+rootConfig[iroot]+","+sync[iroot][isync]+","+rtmretries[iroot][iretry]+","+str(numsc)+"schedQs,"+str(numthrs)+"threads = "+str(simruntime/numTrials)
                simtime_avg[iroot][isync][iretry][numsc-1][thrind] = str(simruntime/numTrials)

                #calculate simtime_std
                for i3 in range(numTrials):
                    time_varsum += pow((trial_buf[i3] - (simruntime/numTrials)), 2)
                simtime_std[iroot][isync][iretry][numsc-1][thrind] = str(math.sqrt(time_varsum/numTrials))
                simtime_stderr[iroot][isync][iretry][numsc-1][thrind] = float(simtime_std[iroot][isync][iretry][numsc-1][thrind])/math.sqrt(numTrials) * tval[numTrials-1]
                del trial_buf[:]
                simruntime = 0 

            del threads[:]
            del schedQs[:]
            
            src.close()
            dst.close()
            os.system("rm " + basedir + "*.tmp")

#print results
#for each locking mechanism, for each schedQ, for each thread, for each config
#syncMechs = ["Atomic", "Mutex"]
syncMechs = [ "Atomic" ]
datastruct = datastruct.lower()
src = open(basedir + model + "-"+migration + "-timeVSthreads-" + datastruct + ".txt", "wb")
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
                retryStr = rtmretries[rootConfig.index("TSXRTM")][i]
                ret = re.search("(\d+)retry", retryStr)
                hdr += "RTMLAZ" + str(ret.group(1)).ljust(5) + "ERRRTMLAZ" + str(i) + " "     
        if "TSXRTMSTRICT" in rootConfig:
            for i in range(len(rtmretries[rootConfig.index("TSXRTMSTRICT")])):
                retryStr = rtmretries[rootConfig.index("TSXRTMSTRICT")][i]
                ret = re.search("(\d+)retry", retryStr)
                hdr += "RTMSTR" + str(ret.group(1)).ljust(5) + "ERRRTMSTR" + str(i) + " "     


        myprint(src, hdr)
        for pithr in range(len(threadsPERschedq[pisc])):
            results = str(threadsPERschedq[pisc][pithr])
            for piroot in range(len(rootConfig)):
                if not (syncMechs[pisync] == "Mutex" and rootConfig[piroot] == "TSXHLE"):
                    if rootConfig[piroot] == "TSXRTM":
                        for piretry in range(len(rtmretries[rootConfig.index("TSXRTM")])):
                            # debugging
                            print "************************"
                            print "rootConfig="+rootConfig[piroot]+";retries="+rtmretries[rootConfig.index("TSXRTM")][piretry]+";threads="+str(threadsPERschedq[pisc][pithr])+";schedq="+str(pisc+1)
                            print simtime_avg[piroot][pisync][piretry][pisc][pithr]
                            print "************************"
                            error = float(simtime_stderr[piroot][pisync][piretry][pisc][pithr])
                            results += " " + str(round(float(simtime_avg[piroot][pisync][piretry][pisc][pithr]), 6)).ljust(10) + " " + str(round(error, 6)).ljust(10)
                    elif rootConfig[piroot] == "TSXRTMSTRICT":
                        for piretry in range(len(rtmretries[rootConfig.index("TSXRTMSTRICT")])):
                            # debugging
                            print "************************"
                            print "rootConfig="+rootConfig[piroot]+";retries="+rtmretries[rootConfig.index("TSXRTMSTRICT")][piretry]+";threads="+str(threadsPERschedq[pisc][pithr])+";schedq="+str(pisc+1)
                            print simtime_avg[piroot][pisync][piretry][pisc][pithr]
                            print "************************"

                            error = float(simtime_stderr[piroot][pisync][piretry][pisc][pithr])
                            results += " " + str(round(float(simtime_avg[piroot][pisync][piretry][pisc][pithr]), 6)).ljust(10) + " " + str(round(error, 6)).ljust(10)
                    else:
                        # debugging
                        print "************************"
                        print "rootConfig="+rootConfig[piroot]+";retries=NAretry;threads="+str(threadsPERschedq[pisc][pithr])+";schedq="+str(pisc+1)
                        print simtime_avg[piroot][pisync][0][pisc][pithr]
                        print "************************"
                        error = float(simtime_stderr[piroot][pisync][0][pisc][pithr])
                        results += " " + str(round(float(simtime_avg[piroot][pisync][0][pisc][pithr]), 6)).ljust(10) + " " + str(round(error, 6)).ljust(10)

            myprint(src, results)
src.close()

#for each locking mechanism, for each thread, for each schedQ, for each config
src = open(basedir + model +"-"+migration + "-timeVSschedQs-" + datastruct + ".txt", "wb")
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
                retryStr = rtmretries[rootConfig.index("TSXRTM")][i]
                ret = re.search("(\d+)retry", retryStr)
                hdr += "RTMLAZ" + str(ret.group(1)).ljust(5) + "ERRRTMLAZ" + str(i) + " "     
        if "TSXRTMSTRICT" in rootConfig:
            for i in range(len(rtmretries[rootConfig.index("TSXRTMSTRICT")])):
                retryStr = rtmretries[rootConfig.index("TSXRTMSTRICT")][i]
                ret = re.search("(\d+)retry", retryStr)
                hdr += "RTMSTR" + str(ret.group(1)).ljust(5) + "ERRRTMSTR" + str(i) + " "     

        myprint(src, hdr)
        for pisc in schedqPERthreads[pithr]:
            results = str(pisc)
            for piroot in range(len(rootConfig)):
                thrind = threadsPERschedq[pisc-1].index(pithr+1)
                if not (syncMechs[pisync] == "Mutex" and rootConfig[piroot] == "TSXHLE"):
                    if rootConfig[piroot] == "TSXRTM":
                        for piretry in range(len(rtmretries[rootConfig.index("TSXRTM")])):
                            # debugging
                            print "************************"
                            print "rootConfig="+rootConfig[piroot]+";retries="+rtmretries[rootConfig.index("TSXRTM")][piretry]+";threads="+str(pithr)+";schedq="+str(schedqPERthreads[pithr][pisc-1])
                            print simtime_avg[piroot][pisync][piretry][pisc-1][pithr]
                            print "************************"
                            error = float(simtime_stderr[piroot][pisync][piretry][pisc-1][thrind])
                            results += " " + str(round(float(simtime_avg[piroot][pisync][piretry][pisc-1][thrind]), 6)).ljust(10) + " " + str(round(error, 6)).ljust(10)
                    elif rootConfig[piroot] == "TSXRTMSTRICT":
                        for piretry in range(len(rtmretries[rootConfig.index("TSXRTMSTRICT")])):
                            # debugging
                            print "************************"
                            print "rootConfig="+rootConfig[piroot]+";retries="+rtmretries[rootConfig.index("TSXRTMSTRICT")][piretry]+";threads="+str(pithr)+";schedq="+str(schedqPERthreads[pithr][pisc-1])
                            print simtime_avg[piroot][pisync][piretry][pisc-1][pithr]
                            print "************************"
                            error = float(simtime_stderr[piroot][pisync][piretry][pisc-1][thrind])
                            results += " " + str(round(float(simtime_avg[piroot][pisync][piretry][pisc-1][thrind]), 6)).ljust(10) + " " + str(round(error, 6)).ljust(10)
                    else:
                        # debugging
                        print "************************"
                        print "rootConfig="+rootConfig[piroot]+";retries=NAretry;threads="+str(pithr)+";schedq="+str(schedqPERthreads[pithr][pisc-1])
                        print simtime_avg[piroot][pisync][0][pisc-1][pithr]
                        print "************************"
                        error = float(simtime_stderr[piroot][pisync][0][pisc-1][thrind])
                        results += " " + str(round(float(simtime_avg[piroot][pisync][0][pisc-1][thrind]), 6)).ljust(10) + " " + str(round(error, 6)).ljust(10)

            myprint(src, results)
src.close()
