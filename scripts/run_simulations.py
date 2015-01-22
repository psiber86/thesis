#!/usr/bin/python

import os
import shutil
import re
import sys
import time
from subprocess import PIPE, Popen
import subprocess
import signal

#simulation configuration parameters

# static thread migration configurations
#numthreads = [ 1, 2, 3, 4, 5, 6, 7 ]
#numSchedQs = [ [1],[1,2],[1,3],[1,2,4],[1,5],[1,2,3,6],[1] ]
#continuous thread migration configurations

numRetries = [ 1, 9, 19 ]
syncMechanisms = ["AtomicLock"]
#syncMechanisms = ["Mutex"]
simruns = 10
#debugging
#numthreads = [ 8 ]
#numSchedQs = [ [1, 2] ]
#numRetries = [ 10000 ]
#simruns = 1

def usage():
    print "run_simulations.py [-sc] <NOTSX|TSXRTM|TSXHLE> <scqscheme> <NO|CONT|XEVENT>"

def config_tsx(use_tsx, retries):
    source = "/home/hayja/warped/configure.ac"
    dest = open(source, "wb")
    src = open(source + '.bak', "r")
    for line in src:
        if 'USETSX_RTM' in line:
            line = re.sub(r'\d', str(int(use_tsx)), line)
        line = line.replace("\r", "")
        dest.write(line)
    src.close()
    dest.close()

    source = "/home/hayja/warped/src/tsx.h"
    dest = open(source, "wb")
    src = open(source + '.bak', "r")
    for line in src:
        if 'TSXRTM_RETRIES' in line:
            line = re.sub(r'\d+', str(retries), line)
        line = line.replace("\r", "")
        dest.write(line)
    src.close()
    dest.close()

def config_migration(migCount):
    source = "/home/hayja/warped/src/ThreadedTimeWarpMultiSet.cpp"
    dest = open(source, "wb")
    src = open(source + '.bak', "r")
    for line in src:
        if 'define MAX_MIGRATION_CNT -' in line:
            line = re.sub(r'-\d+', str(migCount), line)
        elif 'define MAX_MIGRATION_CNT' in line:
            line = re.sub(r'\d+', str(migCount), line)
        line = line.replace("\r", "")
        dest.write(line)
    src.close()
    dest.close()

def config_simulation(threads, schedQs, scqscheme, source, sync, migration):
    dest = open(source, "wb")
    src = open(source + '.bak', "r")
    for line in src:
        if 'WorkerThreadCount' in line:
            line = re.sub(r'\d', str(threads), line)
        if 'ScheduleQCount' in line:
            line = re.sub(r'\d+', str(schedQs), line)
        if 'ScheduleQScheme' in line:
            line = re.sub(r':.*"', ': "'+scqscheme+'"', line)
        if 'SyncMechanism' in line:
            line = re.sub(r':.*"', ': "'+sync+'"', line)
        if 'WorkerThreadMigration' in line:
            if migration == "NO":
                line = re.sub(r':.*', ': false,', line)
            elif migration == "CONT" or migration == "XEVENT":
                line = re.sub(r':.*', ': true,', line)

                
        line = line.replace("\r", "")
        dest.write(line)
    src.close()
    dest.close()

   
def run_models(tsxstr, numqs, numthrs, run, usepcm, scqscheme, model_dir, sync, migration):
    timeout = 600 

#    print "Running raidSim for "+tsxstr+"-"+sync+"-"+str(numqs)+"schedQs"+"-"+str(numthrs)+"threads-"+str(run)+"."+scqscheme
#
#    endtime = time.time() + timeout
#    cmd = "cd /home/hayja/"+model_dir+"/src && sudo /home/hayja/tools/intelPCM/pcm-tsx.x \"./raidSim -c parallel.json --simulate raid/LargeRaid -u 100000\" > /home/hayja/simlogs/log-raidsimlarge-"+tsxstr+"-"+sync+"-"+str(numqs)+"schedQs"+"-"+str(numthrs)+"threads-"+str(run)+"."+scqscheme   
#    p = Popen(cmd, shell=True, stdout=PIPE)
#    while (p.poll() is None) and time.time() < endtime:
#        time.sleep(1)
#
#    pfind = Popen(["pgrep", "raidSim"], stdout=PIPE)
#    for pid in pfind.stdout:
#        subprocess.call(['sudo', 'kill', str(int(pid))])

#    time.sleep(1)
#
#    print "Running iscasSim for "+tsxstr+"-"+sync+"-"+str(numqs)+"schedQs"+"-"+str(numthrs)+"threads-"+str(run)+"."+scqscheme 
#    endtime = time.time() + timeout
#    cmd = "cd /home/hayja/"+model_dir+"/src && sudo /home/hayja/tools/intelPCM/pcm-tsx.x \"./iscasSim -c parallel.json -s iscas/benchfiles/s9234.bench -u 100000\" > /home/hayja/simlogs/log-iscas-"+tsxstr+"-"+sync+"-"+str(numqs)+"schedQs"+"-"+str(numthrs)+"threads-"+str(run)+"."+scqscheme   
#    p = Popen(cmd, shell=True, stdout=PIPE)
#    while (p.poll() is None) and time.time() < endtime:
#        time.sleep(1)
#
#    pfind = Popen(["pgrep", "iscasSim"], stdout=PIPE)
#    for pid in pfind.stdout:
#        subprocess.call(['sudo', 'kill', str(int(pid))])

    time.sleep(1)

    print "Running epidemicSim for "+migration+"mig-"+tsxstr+"-"+sync+"-"+str(numqs)+"schedQs"+"-"+str(numthrs)+"threads-"+str(run)+"."+scqscheme 

    endtime = time.time() + timeout
    cmd = "cd /home/hayja/"+model_dir+"/src && ./epidemicSim -c parallel.json --simulate epidemic/LargeEpidemic.xml -u 100000 > /home/hayja/simlogs/log-hugeepidemicsim-"+migration+"mig-"+tsxstr+"-"+sync+"-"+str(numqs)+"schedQs"+"-"+str(numthrs)+"threads-"+str(run)+"."+scqscheme   
    p = Popen(cmd, shell=True, stdout=PIPE)
    while (p.poll() is None) and time.time() < endtime:
        time.sleep(1)

    pfind = Popen(["pgrep", "epidemicSim"], stdout=PIPE)
    for pid in pfind.stdout:
        subprocess.call(['sudo', 'kill', str(int(pid))])

print "start"
if len(sys.argv) < 4:
    usage()
    sys.exit()
elif sys.argv[1] == "-sc":
    skipCompile = 1   
    tsx = sys.argv[2]
    schedQscheme = sys.argv[3]
    migration = sys.argv[4]
else:
    skipCompile = 0
    tsx = sys.argv[1]
    schedQscheme = sys.argv[2]
    migration = sys.argv[3]

#create backup config files
shutil.copyfile("/home/hayja/warped/configure.ac", "/home/hayja/warped/configure.ac.bak")
shutil.copyfile("/home/hayja/warped/src/tsx.h", "/home/hayja/warped/src/tsx.h.bak")
shutil.copyfile("/home/hayja/models-warped/src/parallel.json", "/home/hayja/models-warped/src/parallel.json.bak")
shutil.copyfile("/home/hayja/warped/src/ThreadedTimeWarpMultiSet.cpp", "/home/hayja/warped/src/ThreadedTimeWarpMultiSet.cpp.bak")

if migration == "CONT":                    
    config_migration(-1)
elif migration == "XEVENT":
    config_migration(50)

if migration == "NO" or migration == "XEVENT":
    numthreads = [ 1, 2, 3, 4, 5, 6, 7 ]
    numSchedQs = [ [1],[1,2],[1,3],[1,2,4],[1,5],[1,2,3,6],[1] ]
elif migration == "CONT":
#    numthreads = [ 1, 2, 3, 4, 5, 6, 7 ]
#    numSchedQs = [ [1],[1,2],[1,2,3],[1,2,3,4],[1,2,3,4,5],[1,2,3,4,5,6],[1,2,3,4,5,6,7, 8, 9, 10, 11] ]
    numthreads = [ 7 ]
    numSchedQs = [ [1, 3, 5, 7, 9] ]

config_simulation(numthreads[0], numSchedQs[0][0], schedQscheme, "/home/hayja/models-warped/src/parallel.json", "HleAtomicLock", migration)

## rerun simulations with different number of retries for TSX only
if tsx == "TSXRTM":
    for i in range(len(syncMechanisms)):
        for i1 in range(len(numRetries)):
            tsxstr = "TSXRTM-" + str(numRetries[i1]) + "retry" 
            config_tsx(True, numRetries[i1])
            if (not skipCompile): 
                os.system("cd /home/hayja/warped/ && make -j7 && make install")
            for i2 in range(len(numthreads)):
                for i3 in range(len(numSchedQs[i2])):
                    print "Writing config files for usetsx_rtm=True, numthreads="+str(numthreads[i2])+", numSchedQs="+str(numSchedQs[i2][i3])
                    config_simulation(numthreads[i2], numSchedQs[i2][i3], schedQscheme, "/home/hayja/models-warped/src/parallel.json", syncMechanisms[i], migration)
                    for i4 in range(simruns):
                        run_models(tsxstr, numSchedQs[i2][i3], numthreads[i2], i4, True, schedQscheme, "models-warped", syncMechanisms[i], migration)
            # need to recompile for different number of retries
            skipComple = 0
 
if tsx == "TSXHLE":
    config_tsx(False, 0)
    tsxstr = "TSXHLE-NAretry"
    if (not skipCompile): 
        os.system("cd /home/hayja/warped/ && make -j7 && make install")
    for i2 in range(len(numthreads)):
        for i3 in range(len(numSchedQs[i2])):
            print "Writing config files for usetsx_hle=True, numthreads="+str(numthreads[i2])+", numSchedQs="+str(numSchedQs[i2][i3])
            config_simulation(numthreads[i2], numSchedQs[i2][i3], schedQscheme, "/home/hayja/models-warped/src/parallel.json", "HleAtomicLock", migration)
            for i4 in range(simruns):
                run_models(tsxstr, numSchedQs[i2][i3], numthreads[i2], i4, True, schedQscheme, "models-warped", "AtomicLock", migration)

if tsx == "NOTSX":
    config_tsx(False, 0)
    tsxstr = "NOTSX-NAretry"
    if (not skipCompile): 
        os.system("cd /home/hayja/warped/ && make -j7 && make install")
    for i in range(len(syncMechanisms)):
        for i1 in range(len(numthreads)):
            for i2 in range(len(numSchedQs[i1])):
                print "Writing config files for use_tsx=False, numthreads="+str(numthreads[i1])+", numSchedQs="+str(numSchedQs[i1][i2])
                config_simulation(numthreads[i1], numSchedQs[i1][i2], schedQscheme, "/home/hayja/models-warped/src/parallel.json", syncMechanisms[i], migration)
                for i3 in range(simruns):
                   run_models(tsxstr, numSchedQs[i1][i2], numthreads[i1], i3, False, schedQscheme, "models-warped", syncMechanisms[i], migration)

shutil.move("/home/hayja/warped/configure.ac.bak", "/home/hayja/warped/configure.ac")
shutil.move("/home/hayja/warped/src/tsx.h.bak", "/home/hayja/warped/src/tsx.h")
shutil.move("/home/hayja/models-warped/src/parallel.json.bak", "/home/hayja/models-warped/src/parallel.json")
print "finish"
