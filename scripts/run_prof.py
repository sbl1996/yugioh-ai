import cProfile
import pstats
import argparse
import runpy
import sys

def main():
    parser = argparse.ArgumentParser(description='Profile a Python script.')
    parser.add_argument('-s', '--sort', default='cumtime', help='Sort key for pstats.Stats (default: %(default)s)')
    parser.add_argument('-n', '--amount', default=20, type=int, help='Number of lines to print (default: %(default)s)')
    parser.add_argument('-r', '--repeat', type=int, default=1, help='Number of times to run the script (default: %(default)s)')
    parser.add_argument('script', help='Python script to profile')
    parser.add_argument('script_args', nargs=argparse.REMAINDER, help='Arguments for the Python script')

    args = parser.parse_args()

    # Set script arguments
    sys.argv = [args.script] + args.script_args

    profile = cProfile.Profile()
    profile.enable()

    for _ in range(args.repeat):
        profile.enable()

        # Run the script
        runpy.run_path(args.script, run_name="__main__")

        profile.disable()

    stats = pstats.Stats(profile).sort_stats(args.sort)
    stats.print_stats(args.amount)

if __name__ == '__main__':
    main()