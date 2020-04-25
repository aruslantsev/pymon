""" Base functions for monitor"""
import os
import time
from subprocess import Popen, PIPE


def get_uptime():
    """ Get system uptime in seconds"""
    with open('/proc/uptime', 'r') as f:
        times = f.read().splitlines()[0].split(' ')
    uptime = float(times[0])
    return {'uptime': uptime}


def get_la():
    """Get load average"""
    with open('/proc/loadavg', 'r') as f:
        la = f.read().splitlines()[0].split(' ')
    la1 = float(la[0])
    la5 = float(la[1])
    la15 = float(la[2])
    proc_raw = la[3].split('/')
    proc_run = int(proc_raw[0])
    proc_total = int(proc_raw[1])
    lastid = int(la[4])

    return {'LA1': la1, 'LA5': la5, 'LA15': la15,
            'running_proc': proc_run, 'total_proc': proc_total,
            'last_pricid': lastid}


def get_cpustats():
    """Get CPU stats"""
    cpustats = {}
    with open('/proc/stat', 'r') as f:
        lines = f.read().splitlines()
    for line in lines:
        if line.startswith('cpu'):
            line = [token for token in line.split(' ') if token != '']
            cpuid = line[0]
            cpuvalues = [int(token) for token in line[1:]]
            cpusum = sum(cpuvalues)
            cpuvalues = [value/cpusum for value in cpuvalues]
            columns = ['user', 'nice', 'system', 'idle', 'iowait',
                       'irq', 'softirq', 'steal', 'guest', 'guest_nice'
                       ][:len(cpuvalues)]
            # We need only corresponding columns, because some of them
            # appeared in recent kernel versions
            cpustats[cpuid] = dict(zip(columns, cpuvalues))

        elif line.startswith('ctxt'):
            cpustats['context_swithces'] = int(line.split(' ')[1])

        elif line.startswith('processes'):
            cpustats['forks'] = int(line.split(' ')[1])

        elif line.startswith('procs_running'):
            cpustats['proc_running'] = int(line.split(' ')[1])

        elif line.startswith('procs_blocked'):
            cpustats['proc_blocked'] = int(line.split(' ')[1])

        elif line.startswith('intr'):
            cpustats['interrupts'] = int(line.split(' ')[1])

        elif line.startswith('softirq'):
            cpustats['softirq'] = int(line.split(' ')[1])

    return cpustats


def get_irqstats():
    """IRQ stats"""
    with open('/proc/interrupts', 'r') as f:
        lines = f.read().splitlines()

    interrupts = {}
    cpus = len([token for token in lines[0].split(' ') if token != ''])

    for line in lines[1:]:
        tokens = [token for token in line.split(' ') if token != '']
        tokens[0] = tokens[0].replace(':', '')
        int_num = tokens[0]

        interrupt = {'number':
                     sum([int(token) for token in tokens[1:(1 + cpus)]])}

        try:
            _ = int(tokens[0])
            # This interrupt has a number
            interrupt['type'] = ' '.join(tokens[(cpus + 1):(cpus + 3)])
            interrupt['devices'] = ' '.join(tokens[(cpus + 3):])
        except ValueError:
            if (int_num != 'ERR') and (int_num != 'MIS'):
                interrupt['type'] = ' '.join(tokens[(cpus + 1):])

        interrupts[int_num] = interrupt
    return interrupts


def get_softirqstats():
    """SoftIRQ stats"""
    with open('/proc/softirqs', 'r') as f:
        lines = f.read().splitlines()

    softirqs = {}

    for line in lines[1:]:
        tokens = [token for token in line.split(' ') if token != '']
        irq_name = tokens[0]
        irq_num = sum([int(token) for token in tokens[1:]])
        softirqs[irq_name] = irq_num

    return softirqs


def get_cpufreqs():
    """Get cpufreq"""
    info = {}
    cpuid = None
    cpuinfo = {}
    with open('/proc/cpuinfo', 'r') as f:
        lines = f.read().splitlines()

    for line in lines:
        if line.startswith('processor'):
            if cpuid is not None:
                info[f'cpu{cpuid}'] = cpuinfo
                cpuinfo = {}
            cpuid = int(line.split(':')[1])
        if line.startswith('model name'):
            cpuinfo['name'] = line.split(' @ ')[0].split(': ')[1]
        if line.startswith('cpu MHz'):
            cpuinfo['frequency'] = float(line.split(': ')[1])
    info[f'cpu{cpuid}'] = cpuinfo

    path_prefix = '/sys/devices/system/cpu/cpufreq/'
    files = ['scaling_min_freq', 'scaling_max_freq', 'scaling_cur_freq']
    for cpuid in range(len(info.keys())):
        path = path_prefix + f'policy{cpuid}/'
        for file in files:
            with open(path + file, 'r') as f:
                freq = int(f.read().splitlines()[0]) / 1000
                info[f'cpu{cpuid}'][file] = freq
    return info


def get_power():
    """Used power"""
    bats = [bat for bat in os.listdir('/sys/class/power_supply') if bat.startswith('BAT')]
    power = {}
    for bat in bats:
        power[bat] = {}
        with open(f'/sys/class/power_supply/{bat}/current_now', 'r') as f:
            current = int(f.read().splitlines()[0])
        with open(f'/sys/class/power_supply/{bat}/voltage_now', 'r') as f:
            voltage = int(f.read().splitlines()[0])
        power[bat]['voltage'] = voltage / 1000000
        power[bat]['current'] = current / 1000000
        power[bat]['power'] = current * voltage / 1000000000000

    power['total'] = sum([value['power'] for value in power.values()])
    return power


def get_sensors():
    """Get info from sensors"""
    process = Popen(['sensors'], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    output = [line for line in stdout.decode('utf-8').split('\n') if line != '']

    sensors = {}
    # We need to find words Package, Core, CPU and Fan
    # I still do not want to use regexps :)
    for line in output:
        if ((line.find('Package') != -1) or (line.find('Core') != -1)
             or (line.find('CPU') != -1) or (line.find('Fan') != -1)):
            line = line.split(':')
            sensor_id = line[0]
            metering = [token for token in line[1].replace('°', ' ').split(' ')
                       if token != '']
            sensors[sensor_id] = {'value': metering[0], 'unit': metering[1]}

    return sensors


def get_smart():
    """Parse smartctl output"""
    return


def get_hddtemp():
    """Get info from hddtemp"""
    disks = [disk for disk in os.listdir('/dev')  if ((disk[:2] == 'sd') or (disk[:2] == 'hd') or (disk[:3] == 'nvme'))]
    print(disks)
    # process = Popen(['sensors'], stdout=PIPE, stderr=PIPE)
    # stdout, stderr = process.communicate()
    # output = [line for line in stdout.decode('utf-8').split('\n') if line != '']
    return


def main():
    """Main loop"""
    start = time.time()
    print(get_uptime())
    print(get_la())
    print(get_cpustats())
    print(get_irqstats())
    print(get_softirqstats())
    print(get_cpufreqs())
    print(get_power())

    print(get_sensors())
    print(get_hddtemp())

    end = time.time()
    print(end - start)
    return


if __name__ == '__main__':
    main()
