#!/usr/bin/python3

import libvirt
import sys
import psutil
import time
from datetime import datetime

# all memory sizes are in 1k blocks (1024 bytes)
MB = 1024
GB = 1024*MB

# Total physical memory of the host system (converted from bytes to 1k blocks)
total_phys_mem = psutil.virtual_memory().total/1024

# Maximum memory to allocate for all VMs together (reserve some margin for the host system)
max_total_mem = total_phys_mem - 4*GB

# Free memory to aim for in a single VM (absolute)
free_mem_target = 4*GB

# Free memory to aim for in a single VM (per core)
free_mem_per_core_target = 256*MB


# Open connection to Hypervisor
try:
    conn = libvirt.open(None)
except libvirt.libvirtError:
    print('Failed to open connection to the hypervisor')
    sys.exit(1)

vmConfigured = {}

while True:
    
    print(f'------------------ {datetime.now()}')

    domains = conn.listAllDomains()
    
    dom_new_mem_size = [None] * len(domains)
    
    for idx, dom in enumerate(domains) :
        if(dom.state()[0] != libvirt.VIR_DOMAIN_RUNNING) :
            vmConfigured[dom.name()] = False
            continue

        if dom.name() not in vmConfigured or not vmConfigured[dom.name()]:
            dom.setMemoryStatsPeriod(1)
            vmConfigured[dom.name()] = True
        
        dom_free_mem_target = max(free_mem_per_core_target * dom.maxVcpus(), free_mem_target)
        
        dom_stats = dom.memoryStats()
        
        # positive delta: more free ram than target; negative delta: less free than target
        delta = dom_stats['usable'] - dom_free_mem_target
        
        # compute new wanted memory size for VM, and clamp it and round it to full GB
        dom_new_mem_size[idx] = dom_stats['actual'] - delta
        dom_new_mem_size[idx] = max(dom_new_mem_size[idx], dom_free_mem_target)
        dom_new_mem_size[idx] = min(dom_new_mem_size[idx], dom.maxMemory())
        dom_new_mem_size[idx] = round(dom_new_mem_size[idx]/(4*GB))*4*GB
    
    # compute sum of wanted mem of all VMs
    total_wanted_mem = 0
    for idx, dom in enumerate(domains) :
        if dom_new_mem_size[idx] is None:
            continue
        dom_stats = dom.memoryStats()
        print(f"{dom.name():<40} {dom_stats['actual']/GB:4.0f} GB -> {dom_new_mem_size[idx]/GB:4.0f} GB")
        total_wanted_mem += dom_new_mem_size[idx]

    print(f"{'(total)':<40}            {total_wanted_mem/GB:4.0f} GB")
    
    # check if max_total_mem is violated
    if total_wanted_mem > max_total_mem:
        factor = max_total_mem/total_wanted_mem
        print('')
        print(f'Excessive memory use detected, scaling down all VMs by {factor}. New values:')
        for idx, dom in enumerate(domains) :
            if dom_new_mem_size[idx] is None:
                continue
            dom_new_mem_size[idx] *= factor
            dom_stats = dom.memoryStats()
            print(f"{dom.name():<40} {dom_stats['actual']/GB:4.0f} GB -> {dom_new_mem_size[idx]/GB:4.0f} GB")

    # apply new values to VMs
    for idx, dom in enumerate(domains) :
        if dom_new_mem_size[idx] is None:
            continue
        dom.setMemory(int(round(dom_new_mem_size[idx])))
    
    
    time.sleep(2)
    


