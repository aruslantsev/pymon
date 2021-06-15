import json
import sys

from base_funcs import collect_stats


def main():
    if (len(sys.argv) == 2) and isinstance(sys.argv[1], str):
        with open(sys.argv[1], 'a') as fd:
            date, stats = collect_stats()
            fd.write(json.dumps({date: stats}, indent=None) + '\n')


if __name__ == "__main__":
    main()
