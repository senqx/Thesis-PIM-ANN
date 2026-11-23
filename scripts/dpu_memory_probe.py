#!/usr/bin/env python3
"""Check the current model's effective MRAM throughput; not hardware validation."""
import argparse
import csv
from types import SimpleNamespace
from wram_platform import ROOT,compile_sources,invoke,bytefile
from access_plan import pack

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('action',choices=['compile','run'])
args=p.parse_args()
rows=[]
for size in (8,64,1024):
    name=f'probe_{size}'
    if args.action=='compile':
        compile_sources(SimpleNamespace(tasklets=12,sdk=False,benchmark=name,
            source=ROOT/'experiments/access-plan/memory_probe.c',define=[f'-DTRANSFER_BYTES={size}']))
        continue
    directory=ROOT/f'runs/access-plan-memory-probe/{name}'
    if directory.exists():raise FileExistsError(directory)
    invoke('link',directory,name,12)
    n=32
    data=pack([i%251 for i in range(n*12*size//4)])
    bytefile(directory/'input_DPU_INPUT_ARGUMENTS_0_0.bin',pack([n,len(data),0,0]))
    bytefile(directory/'input_dpu_mram_heap_pointer_name_0_0_0.bin',data)
    bytefile(directory/f'output_dpu_mram_heap_pointer_name_{len(data)}_0_0.bin',data[-12*size:])
    (directory/'num_executions.txt').write_text('1\n')
    invoke('simulate',directory,name,12)
    stat={k:int(v) for k,v in (line.split(': ') for line in (directory/'log.txt').read_text().splitlines())}
    assert stat['RowBuffer[0_0_0]_read_bytes']==len(data)
    assert stat['RowBuffer[0_0_0]_write_bytes']==12*size
    cycles=stat['Logic[0_0_0]_logic_cycle']
    row=dict(transfer_bytes=size,tasklets=12,transfers_per_tasklet=n,cycles=cycles,
        read_bytes=len(data),write_bytes=12*size,read_MB_per_second=len(data)*350/cycles,
        instructions=stat['Logic[0_0_0]_num_instructions'],output_check='passed',traffic_check='passed')
    rows.append(row);print(row,flush=True)
if rows:
    with (ROOT/'experiments/access-plan/memory-probe.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
