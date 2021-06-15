"""Base functions for monitor"""
import datetime
import json
import os
import re
from subprocess import Popen, PIPE


debug = False

def get_baseinfo():
    """Get load average"""
    with open('/proc/uptime', 'r') as f:
        times = f.read().splitlines()[0].split(' ')
    uptime = float(times[0])
    with open('/proc/loadavg', 'r') as f:
        la = f.read().splitlines()[0].split(' ')
    la1 = float(la[0])
    la5 = float(la[1])
    la15 = float(la[2])
    proc_raw = la[3].split('/')
    proc_run = int(proc_raw[0])
    proc_total = int(proc_raw[1])
    lastid = int(la[4])

    return {'uptime': uptime, 'LA1': la1, 'LA5': la5, 'LA15': la15,
            'running_processes': proc_run, 'total_processes': proc_total,
            'last_processid': lastid}


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
            cpustats['context_switches'] = int(line.split(' ')[1])

        elif line.startswith('processes'):
            cpustats['forks'] = int(line.split(' ')[1])

        elif line.startswith('procs_running'):
            cpustats['processes_running'] = int(line.split(' ')[1])

        elif line.startswith('procs_blocked'):
            cpustats['processes_blocked'] = int(line.split(' ')[1])

        elif line.startswith('intr'):
            cpustats['interrupts'] = int(line.split(' ')[1])

        elif line.startswith('softirq'):
            cpustats['softirqs'] = int(line.split(' ')[1])

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

        interrupt = {'sum':
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
        irq_name = tokens[0].replace(':', '')
        irq_num = sum([int(token) for token in tokens[1:]])
        softirqs[irq_name] = irq_num

    return softirqs


def get_meminfo():
    """Parse /proc/meminfo"""
    with open('/proc/meminfo', 'r') as f:
        lines = f.read().splitlines()

    meminfo = {}
    for line in lines:
        line = [token for token in line.split(' ') if token != '']
        if line[0] == 'MemTotal:':
            meminfo['total'] = int(line[1])
            meminfo['unit'] = line[2]
        if line[0] == 'MemFree:':
            meminfo['free'] = int(line[1])
        if line[0] == 'MemAvailable:':
            meminfo['available'] = int(line[1])
        if line[0] == 'Buffers:':
            meminfo['buffers'] = int(line[1])
        if line[0] == 'Cached:':
            meminfo['cached'] = int(line[1])
        if line[0] == 'SwapTotal:':
            meminfo['swaptotal'] = int(line[1])
        if line[0] == 'SwapFree:':
            meminfo['swapfree'] = int(line[1])
        if line[0] == 'Dirty:':
            meminfo['dirty'] = int(line[1])
        if line[0] == 'Mapped:':
            meminfo['mapped'] = int(line[1])
        if line[0] == 'Shmem:':
            meminfo['shmem'] = int(line[1])
        if line[0] == 'Slab:':
            meminfo['slab'] = int(line[1])
        if line[0] == 'PageTables:':
            meminfo['pagetbl'] = int(line[1])

    return meminfo


def get_diskstats():
    """Disk usage"""
    def parse_line(outline):
        """parse line"""
        outline = [token for token in outline.split(' ') if token != '']
        total = int(outline[1])
        used = int(outline[2])
        avail = int(outline[3])
        percent_used = int(outline[4].replace('%', '').replace('-', '0'))
        return total, used, avail, percent_used

    process = Popen(['df'], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').splitlines()
    mountpoints = []
    devices = []
    for line in stdout[1:]:
        line = line.split(' ')
        mountpoints.append(line[-1])
        devices.append(line[0])

    diskstats = {}
    for mountpoint, device in zip(mountpoints, devices):
        process = Popen(['df', '-k', mountpoint], stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        stdout = stdout.decode('utf-8').splitlines()[1]
        kbtotal, kbused, kbavail, kbpercent = parse_line(stdout)

        process = Popen(['df', '-i', mountpoint], stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        stdout = stdout.decode('utf-8').splitlines()[1]
        itotal, iused, iavail, ipercent = parse_line(stdout)
        diskstats[mountpoint] = {
            'device': device,
            'kb_total': kbtotal, 'kb_used': kbused,
            'kb_avail': kbavail, 'kb_percent': kbpercent,
            'inodes_total': itotal, 'inodes_used': iused,
            'inodes_avail': iavail, 'inodes_percent': ipercent
        }
    return diskstats


def get_users():
    """Get number of users in system"""
    process = Popen(['who'], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').splitlines()

    all_users = []
    tty = 0
    pts = 0
    for line in stdout:
        line = [token for token in line.split(' ') if token != '']
        if line[0] not in all_users:
            all_users.append(line[0])
        if line[1].startswith('tty'):
            tty += 1
        if line[1].startswith('pts'):
            pts += 1

    users = {'users': all_users, 'tty': tty,  'pts': pts, 'total': tty + pts}

    return users


def get_sensors():
    """Get info from sensors"""
    sensors = {}
    
    try:
        process = Popen(['sensors'], stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        output = [line for line in stdout.decode('utf-8').split('\n')
                  if line != '']
        # We need to find words Package, Core, CPU and Fan
        for line in output:
            if re.search(r'Package|Core|CPU|[Ff]an', line):
                line = line.split(':')
                sensor_id = line[0]
                metering = [token for token in 
                            line[1].replace('°', ' ').split(' ') 
                            if token != '']
                sensors[sensor_id] = {'value': metering[0], 
                                      'unit': metering[1]}
    except FileNotFoundError:
        pass

    return sensors


def get_smart():
    """Parse smartctl output"""
    disks = sorted([disk for disk in os.listdir('/dev')
                    if (re.search(r'\b[hs]d\D\b', disk)
                        or re.search(r'\bnvme[0-9]\b', disk))])
    diskinfo = {}
    for disk in disks:
        try:
            process = Popen(['smartctl', '-i', '/dev/{}'.format(disk)],
                            stdout=PIPE, stderr=PIPE)
            stdout, stderr = process.communicate()
            stdout = stdout.decode('utf-8').splitlines()

            model = None
            sn = None
            smart_attrs = []

            smart_start = False
            value_position = None

            for line in stdout:
                if line.startswith('Device Model'):
                    model = line.split(':')[1].lstrip(' ')
                if line.startswith('Serial Number'):
                    sn = line.split(':')[1].lstrip(' ')

            process = Popen(['smartctl', '-A', '/dev/{}'.format(disk)],
                            stdout=PIPE, stderr=PIPE)
            stdout, stderr = process.communicate()
            stdout = stdout.decode('utf-8').splitlines()
            for line in stdout:
                if smart_start and line != '':
                    line = [token for token in line.split(' ') if token != '']
                    smart_attrs.append({'num': int(line[0]), 'name': line[1],
                                        'value': int(line[value_position])})

                if not smart_start and line.startswith('ID#'):
                    smart_start = True
                    value_position = len(
                        [token for token in line.split(' ') if token != '']
                    ) - 1

            diskinfo[disk] = {
                'model': model, 's/n': sn, 'attributes': smart_attrs}
        except FileNotFoundError:
            pass
    return diskinfo


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
                info['cpu{}'.format(cpuid)] = cpuinfo
                cpuinfo = {}
            cpuid = int(line.split(':')[1])
        if line.startswith('model name'):
            cpuinfo['name'] = line.split(' @ ')[0].split(': ')[1]
        if line.startswith('cpu MHz'):
            cpuinfo['frequency'] = float(line.split(': ')[1])
    info['cpu{}'.format(cpuid)] = cpuinfo

    path_prefix = '/sys/devices/system/cpu/cpufreq/'
    files = ['scaling_min_freq', 'scaling_max_freq', 'scaling_cur_freq']
    for cpuid in range(len(info.keys())):
        path = path_prefix + 'policy{}/'.format(cpuid)
        for file in files:
            try:
                with open(path + file, 'r') as f:
                    freq = int(f.read().splitlines()[0]) / 1000
                    info['cpu{}'.format(cpuid)][file] = freq
            except FileNotFoundError:
                pass
    return info


def get_power():
    """Used power"""
    try:
        bats = [bat for bat in os.listdir('/sys/class/power_supply') 
                if bat.startswith('BAT')]
    except FileNotFoundError:
        bats = []
        
    power = {}
    for bat in bats:
        power[bat] = {}
        try:
            with open('/sys/class/power_supply/{}/current_now'.format(
                    bat), 'r') as f:
                current = int(f.read().splitlines()[0]) / 1000000
        except FileNotFoundError:
            current = 0
        try:
            with open('/sys/class/power_supply/{}/voltage_now'.format(
                    bat), 'r') as f:
                voltage = int(f.read().splitlines()[0]) / 1000000
        except FileNotFoundError:
            current = 0
        try:
            with open('/sys/class/power_supply/{}/power_now'.format(
                    bat), 'r') as f:
                batpower = int(f.read().splitlines()[0]) / 1000000
        except FileNotFoundError:
            batpower = current * voltage
        power[bat]['voltage'] = voltage
        power[bat]['current'] = current
        power[bat]['power'] = batpower

    power['total'] = sum([value['power'] for value in power.values()])
    return power


def get_if():
    """Parse ifconfig output"""
    interfaces = os.listdir('/sys/class/net')
    netstats = {}
    for device in interfaces:
        stats = {}
        process = Popen(['ifconfig', device], stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        stdout = stdout.decode('utf-8').splitlines()
        for line in stdout:
            if 'RX' in line or 'TX' in line:
                if 'RX' in line:
                    prefix = 'rx_'
                else:
                    prefix = 'tx_'
                line = [token for token in line.split(' ') if token != '']
                for i, token in enumerate(line):
                    if token == 'packets':
                        stats[prefix + 'packets'] = int(line[i + 1])
                    if token == 'bytes':
                        stats[prefix + 'bytes'] = int(line[i + 1])
                    if token == 'errors':
                        stats[prefix + 'errors'] = int(line[i + 1])
                    if token == 'dropped':
                        stats[prefix + 'dropped'] = int(line[i + 1])

        netstats[device] = stats
    return netstats


def get_netstat():
    """Netstat"""
    def analyze_out(out):
        """analyze output lines"""
        listen = 0
        established = 0
        for outline in out:
            if 'LISTEN' in outline:
                listen += 1
            if 'ESTABLISHED' in outline:
                established += 1
        return listen, established

    process = Popen(['netstat', '-au'], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').splitlines()
    udplisten, udpestablished = analyze_out(stdout)

    process = Popen(['netstat', '-at'], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').splitlines()
    tcplisten, tcpestablished = analyze_out(stdout)

    process = Popen(['netstat', '-ax'], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').splitlines()
    socklisten = 0
    sockconn = 0
    for line in stdout:
        if 'LISTENING' in line:
            socklisten += 1
        if 'CONNECTED' in line:
            sockconn += 1

    netstat = {'tcp_listen': tcplisten, 'tcp_established': tcpestablished,
               'udp_listen': udplisten, 'udp_established': udpestablished,
               'sock_listen': socklisten, 'sock_connected': sockconn}
    return netstat


def collect_stats():
    """Run all functions"""
    sysstats = {}
    sysstats.update({'base': get_baseinfo()})
    sysstats.update({'cpustats': get_cpustats()})
    sysstats.update({'IRQs': get_irqstats()})
    sysstats.update({'SoftIRQs': get_softirqstats()})
    sysstats.update({'meminfo': get_meminfo()})
    sysstats.update({'disk': get_diskstats()})
    sysstats.update({'users': get_users()})
    try:
        sysstats.update({'sensors': get_sensors()})
    except Exception as e:
        if debug:
            print(e)
    try:
        sysstats.update({'SMART': get_smart()})
    except Exception as e:
        if debug:
            print(e)
    try:
        sysstats.update({'cpufreqs': get_cpufreqs()})
    except Exception as e:
        if debug:
            print(e)
    try:
        sysstats.update({'power': get_power()})
    except Exception as e:
        if debug:
            print(e)
    sysstats.update({'net_if': get_if()})
    sysstats.update({'netstat': get_netstat()})
    date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    return date, sysstats


def main():
    """Main loop"""
    date, stats = collect_stats()
    print(json.dumps({date: stats}, indent=None))
    return


if __name__ == '__main__':
    main()
