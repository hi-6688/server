import sys
import re

def strings(filename, min=4):
    with open(filename, "rb") as f:
        result = ""
        for b in f.read():
            c = chr(b)
            if " " <= c <= "~":
                result += c
            else:
                if len(result) >= min:
                    print(result)
                result = ""

if __name__ == "__main__":
    strings(sys.argv[1])
