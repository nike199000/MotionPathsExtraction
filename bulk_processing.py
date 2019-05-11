import configparser
import sys
import subprocess
import multiprocessing
import time
import glob

import detect_and_track


class BulkProcessor(object):

    def __init__(self):
        
        num_nvidia_gpus = str(subprocess.check_output(["nvidia-smi", "-L"])).count('UUID')
        
        config = configparser.ConfigParser()
        config.sections()
        config.read('bulk_config.ini')
        
        self.gpu_ids = config.items( "Gpus" )
        self.configs = config.items( "Configs" )
        self.inputs = config.items( "Input" )
        self.num_instances = config.items( "Instances_per_gpu" )
        self.file_types = config.items( "File_type" )
        
        if len(self.gpu_ids) < 1 or len(self.gpu_ids) > num_nvidia_gpus:
        	sys.exit('Number of processors to use must be greater than 0 and smaller than gpus available')
        
        if len(self.gpu_ids) != len(self.configs):
        	sys.exit('len(self.gpu_ids) != len(self.configs) != len(self.inputs) != len(self.outputs)')
        
    def process(self, i, j, count, file):
        
        print("Starting process %d on GPU %d" % (j, int(self.gpu_ids[i][1]))) 
        
        try:
            process = detect_and_track.App(True,
                                           True,
                                           int(self.gpu_ids[i][1]),
                                           j, 
                                           str(self.configs[i][1]), 
                                           str(self.inputs[count][1]), 
                                           str(file))
            process.start_bulk()
            print("Process on GPU %d stopped" % int(self.gpu_ids[i][1]))
        
        except Exception:
    
                e = sys.exc_info()[0] + '' + sys.exc_info()[1]
                print("Error: " + str(e))
                raise       
           
if __name__ == '__main__':

    try:
        multiprocessing.set_start_method('spawn')
    except RuntimeError:
        pass
    
    
    bulk = BulkProcessor()                    
           
    proc_dict = {}
    count = 0
    while True:
        procs_tmp = []
        for i in range(len(bulk.gpu_ids)):  
            for j in range(int(bulk.num_instances[i][1])):            
                
                if str(i) + str(j) not in proc_dict:
                    glob_list = glob.glob(bulk.inputs[count][1] + '/**/*.' + bulk.file_types[i][1], recursive=True)            
                    procs = []
                    for t in range(0, len(glob_list)):
                        p = multiprocessing.Process(target=bulk.process, args=(i, j, count, glob_list.pop(0)))
                        procs.append(p)
                    proc_dict[str(i) + str(j)] = procs
                
                    count += 1
                    
                if len(proc_dict[str(i) + str(j)]) > 0:
                    proc = proc_dict[str(i) + str(j)].pop(0)          
                    procs_tmp.append(proc)
                    proc.start()
                    time.sleep(20)
                else:
                    proc_dict.pop(str(i) + str(j))                
                            
        for proc in procs_tmp:
            proc.join()
        
        if len(proc_dict) == 0:
            break