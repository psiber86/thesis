#!/usr/bin/python

import os
import re
import sys
import shutil
import math

#row = #numSchedQs; #col = #numThreads
threads = []
schedQs = []
retries = []
simtime_avg = [] 
simtime_std = [] 
commits_avg = []
commits_std = []
aborts_avg = [] 
aborts_std = [] 
trial_buf = []
commits_buf = []
aborts_buf = []
simruntime = 0

def usage():
    print "ext_simtimes.py /path/to/log-<model> <t value based on confidence level>"
    sys.exit()

if len(sys.argv) != 3:
    usage()
else:
    logconfig = sys.argv[1]
    tval = float(sys.argv[2])

ret = re.search("(^.+/?)log-(.+?)$", logconfig)
basedir = ret.group(1)
model = ret.group(2)

#determine how many different TSX confis there are
os.system("cd " + basedir + " && ls " + logconfig + "-TSX-* > tsxconfigs.tmp")
src = open(basedir + "tsxconfigs.tmp")
for line in src:
    ret = re.search(".*log-.*-TSX-([0-9]+)", line)
    if int(ret.group(1)) not in retries:
        retries.append(int(ret.group(1)))
src.close()
os.remove(basedir + "tsxconfigs.tmp")
retries.sort()

ret = re.search("(^.+/?)log-(.+?)$", logconfig)
basedir = ret.group(1)
target = [ basedir + "simtimes-" + ret.group(2) + "-NOTSX" ]
target_tsxstats = []
cmd = [ "cd " + ret.group(1) + " && grep \"Simulation complete\" " + logconfig + "-NOTSX-* > " + target[0] ]
for i in range(len(retries)):
   target.append(basedir + "simtimes-" + ret.group(2) + "-TSX-" + str(retries[i]) + "retry") 
   target_tsxstats.append(basedir + "tsxstats-" + ret.group(2) + "-TSX-" + str(retries[i]) + "retry")
   cmd.append("cd " + ret.group(1) + " && grep \"Simulation complete\" " + logconfig + "-TSX-" + str(retries[i]) +"retry-* > " + target[i+1])

for i in range(len(target)):
    os.system(cmd[i])
    shutil.move(target[i], target[i] + '.tmp')
    src = open(target[i] + '.tmp')
    dst = open(target[i] + '.txt', "wb")
    if i > 0:
        dst_tsxstats = open(target_tsxstats[i-1] + '.txt', "wb") 
    i2 = 1
    for line in src:
        #config changes every 10 lines 
        ret = re.search(".*(log-.*threads-?)([0-9]+?)", line)
        srchfile = ret.group(1) + ret.group(2) 
        if int(ret.group(2)) == 0:
            #determine new configuration
            if i == 0:
                ret = re.search(".*log-.*-NOTSX-([0-9]?)schedQs-([0-9]?)threads-.*", line)
            else:
                ret = re.search(".*log-.*-TSX-.*-([0-9]?)schedQs-([0-9]?)threads-.*", line)

            numsc = int(ret.group(1))
            numthrs = int(ret.group(2))

            if numsc not in schedQs:
                schedQs.append(numsc)
                threads.append([])
                simtime_avg.append([])
                simtime_std.append([])
                commits_avg.append([])
                commits_std.append([])
                aborts_avg.append([])
                aborts_std.append([])
            for i3 in range(len(schedQs)):
                if numthrs not in threads[i3]:
                    threads[i3].append(numthrs)
                    simtime_avg[i3].append([])
                    simtime_std[i3].append([])
                    commits_avg[i3].append([])
                    commits_std[i3].append([])
                    aborts_avg[i3].append([])
                    aborts_std[i3].append([])

            dst.write("********************************\n")
            dst.write("* " + str(numthrs) + " Threads - " + str(numsc) + " Schedule Queue(s)\n")
            dst.write("********************************\n")
            if i > 0:
                dst_tsxstats.write("********************************\n")
                dst_tsxstats.write("* " + str(numthrs) + " Threads - " + str(numsc) + " Schedule Queue(s)\n")
                dst_tsxstats.write("********************************\n")

        #extract simtimes
        ret = re.findall(r"\d+\.\d+e[-+]?\d+", line)
        if ret: 
            time = float(ret[0])
            dst.write( str(time) + "\n")
            simruntime += time
            trial_buf.append(time)
        else:
            ret = re.findall(r"\d+\.\d+", line)
            time = float(ret[0])
            dst.write( str(time) + "\n")
            simruntime += time
            trial_buf.append(time)

        #extract tsx stats; 3 lines per file
        if i > 0:
            totcommits = 0
            totaborts = 0
            os.system("cd " + basedir + " && grep \"TSX\" " + basedir + srchfile + "* > " + target_tsxstats[i-1]) 
            shutil.move(target_tsxstats[i-1], target_tsxstats[i-1] + '.tmp')
            src_tsxstats = open(target_tsxstats[i-1] + '.tmp')
            tmp = src_tsxstats.readline()
            for i4 in range(2): 
                tmp = src_tsxstats.readline()
                ret = re.findall(r"\d+$", tmp)
                totcommits += int(ret[0])
                commits += totcommits
                tmp = src_tsxstats.readline()
                ret = re.findall(r"\d+$", tmp)
                totaborts += int(ret[0])
                aborts += totaborts
                tmp = src_tsxstats.readline()
                if (not tmp):
                    break
            commits_buf.append(totcommits)
            aborts_buf.append(totaborts)

        #dont calculate stats until 10 lines have been parsed
        if i2 % 10 == 0:
            time_varsum = 0
            commits_varsum = 0
            aborts_varsum = 0
            scind = schedQs.index(numsc)
            thrind = threads[scind].index(numthrs)
            simtime_avg[scind][thrind].append(str(simruntime/10))
            if i > 0:
                commits_avg[scind][thrind].append(str(commits/10))
                aborts_avg[scind][thrind].append(str(aborts/10))
            #calculate simtime_std
            for i3 in range(10):
                time_varsum += pow((trial_buf[i3] - (simruntime/10)), 2)
                if i > 0:
                    commits_varsum += pow((commits_buf[i3] - (commits/10)), 2)
                    aborts_varsum += pow((aborts_buf[i3] - (aborts/10)), 2)
            simtime_std[scind][thrind].append(str(math.sqrt(time_varsum/10)))
            if i > 0:
                commits_std[scind][thrind].append(str(math.sqrt(commits_varsum/10)))
                aborts_std[scind][thrind].append(str(math.sqrt(aborts_varsum/10)))
            del trial_buf[:]
            del commits_buf[:]
            del aborts_buf[:]
            simruntime = 0 
            commits = 0
            aborts = 0

        i2 += 1
    
    src.close()
    dst.close()
    os.system("rm *.tmp")
    
#print and log summary of runtimes
hdr = "# NOTSX      ERRNOTSX   "
for i in range(len(retries)):
    hdr += "TSX" + str(retries[i]).ljust(7) + " TSXERR" + str(i) + "    "     

summary = open(basedir + "summary-simtimes-" + model, "wb")
for i1 in range(len(schedQs)):
    print "# Simulation Runtime Summary for " + str(schedQs[i1]) + " Schedule Queue(s)"
    summary.write("# Simulation Runtime Summary for " + str(schedQs[i1]) + " Schedule Queue(s)\n")
    print hdr
    summary.write(hdr + "\n")
    for i2 in range(len(threads[i1])):
        results = str(threads[i1][i2])
        for i3 in range(len(simtime_avg[i1][i2])):
            error = tval*(float(simtime_std[i1][i2][i3])/math.sqrt(10)) 
            results += " " + str(round(float(simtime_avg[i1][i2][i3]), 9)).ljust(10) + " " + str(round(error, 8)).ljust(10) 
        print results
        summary.write(results + "\n")
hdr = "# "
for i in range(len(retries)):
    hdr += "TSX" + str(retries[i]).ljust(9) + " TSXERR" + str(i) + "      "     
for i1 in range(len(schedQs)):
    print "# TSX Commits Summary for " + str(schedQs[i1]) + " Schedule Queue(s)"
    summary.write("# TSX Commits Summary for " + str(schedQs[i1]) + " Schedule Queue(s)")
    print hdr
    summary.write(hdr + "\n")
    for i2 in range(len(threads[i1])):
        results = str(threads[i1][i2])
        for i3 in range(len(commits_avg[i1][i2])):
            error = tval*(float(commits_std[i1][i2][i3])/math.sqrt(10)) 
            results += " " + str(int(commits_avg[i1][i2][i3])).ljust(12) + " " + str(round(error, 4)).ljust(12) 
        print results
        summary.write(results + "\n")
for i1 in range(len(schedQs)):
    print "# TSX Aborts Summary for " + str(schedQs[i1]) + " Schedule Queue(s)"
    summary.write("# TSX Aborts Summary for " + str(schedQs[i1]) + " Schedule Queue(s)")
    print hdr
    summary.write(hdr + "\n")
    for i2 in range(len(threads[i1])):
        results = str(threads[i1][i2])
        for i3 in range(len(aborts_avg[i1][i2])):
            error = tval*(float(aborts_std[i1][i2][i3])/math.sqrt(10)) 
            results += " " + str(int(aborts_avg[i1][i2][i3])).ljust(12) + " " + str(round(error, 4)).ljust(12) 
        print results
        summary.write(results + "\n")

