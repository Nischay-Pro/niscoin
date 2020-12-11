#!/usr/bin/env python
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--string', "-s", help='Input String', nargs='+')
    args = parser.parse_args()


if __name__ == "__main__":
    main()