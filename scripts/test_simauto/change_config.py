#!/usr/bin/python

import os
import shutil
import re

#simulation configuration parameters
use_tsx = [ False, True ]
numthreads = [4] 
numSchedQs = [[2]] 
simruns = [1] 
#use_tsx = [ False, True ]
#numthreads = [ 2, 3, 4, 5, 6, 7, 8 ]
#numSchedQs = [ [1, 2], [1], [1, 2, 4], [1], [1, 2, 3, 6], [1], [1, 2, 4, 8] ]
#simruns = 10

def config_tsx(use_tsx):
    source = '/home/hayja/warped/configure.ac'
    shutil.move(source, source + '.bak')
    dest = open(source, "wb")
    src = open(source + '.bak', "r")
    for line in src:
        if '[USE_TSX], 1' in line and not use_tsx:
            dest.write('AC_DEFINE([USE_TSX], 0, [Define to use TSX hardware on supported Haswell processors])\n')
        elif '[USE_TSX], 0' in line and use_tsx:
            dest.write('AC_DEFINE([USE_TSX], 1, [Define to 1 to use TSX hardware on supported Haswell processors])\n')
        else:
            line = line.replace("\r", "")
            dest.write(line)
    src.close()
    dest.close()

def config_simulation(threads, schedQs):
    dest = open(source, "wb")
    src = open(source + '.bak', "r")
    for line in src:
        if 'WorkerThreadCount' in line:
            line = re.sub(r'\d', str(threads), line)
        if 'ScheduleQCount' in line:
            line = re.sub(r'\d', str(schedQs), line)
        line = line.replace("\r", "")
        dest.write(line)
    src.close()
    dest.close()

print "start"
source = '/home/hayja/models-warped/src/parallel.json'    
shutil.move(source, source+ '.bak')
for i1 in range(len(use_tsx)):
    config_tsx(use_tsx[i1])
    os.system("cd /home/hayja/warped && autoreconf -i && ./configure --with-mpiheader=/usr/include/mpich2 --with-mpich=/usr/lib/mpich2 --prefix=/home/hayja/lib/warped && make && make install")
    for i2 in range(len(numthreads)):
        for i3 in range(len(numSchedQs[i2])):
            print "Writing config files for use_tsx="+str(use_tsx[i1])+", numthreads="+str(numthreads[i2])+", numSchedQs="+str(numSchedQs[i2][i3])
            config_simulation(numthreads[i2], numSchedQs[i2][i3], str(numthreads[i2])+"-"+str(numSchedQs[i2][i3]))
            for i4 in range(len(simruns)):
                if use_tsx[i1]:
                    tsxstr = "TSX"
                else:
                    tsxstr = "NOTSX"
                
                cmd = "cd /home/hayja/models-warped/src && /home/hayja/tools/intelPCM/pcm-tsx.x ./pingpong -c parallel.json | tee log-pingpong-"+tsxstr+"-"+str(numthreads[i2])+"threads-"+str(numSchedQs[i2][i3])+"schedQs" 
                os.system(cmd)

                cmd = "cd /home/hayja/models-warped/src && /home/hayja/tools/intelPCM/pcm-tsx.x ./raidSim -c parallel.json --simulate raid/LargeRaid | tee log-raidsim-"+tsxstr+"-"+str(numthreads[i2])+"threads-"+str(numSchedQs[i2][i3])+"schedQs" 
                os.system(cmd)

print "finish"
