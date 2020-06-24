"""Agent"""
from base_funcs import collect_stats
import sys


def main():
    """main"""
    if len(sys.argv) != 2:
        print("This script takes exactly one argument. Run it as " + sys.argv[0] + " outfile'")
        sys.exit(1)
    fname = sys.argv[1]
    f = open(fname, 'a')
    date, stats = collect_stats()
    f.write(str({date: stats}) + '\n')
    f.close()
    sys.exit(0)


if __name__ == "__main__":
    main()
