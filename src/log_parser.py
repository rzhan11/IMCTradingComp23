import json
import sys
from pathlib import Path

def process_file(fname):

    input_file = Path(fname)

    print("Reading from input file", input_file)
    with open(input_file, "r") as f:
        text = f.read()


    start_sep = "__mark"
    end_sep = "__end"
    
    # start_sep = "__json_start"
    # end_sep = "__json_end"

    # split on start_sep
    splits = text.split(start_sep)

    # skip first entry (before __mark)
    splits = splits[1:]

    # split on end_sep
    splits = [s.split(end_sep) for s in splits]

    # only keep before end_sep
    splits = [s[0] for s in splits]
    splits = [json.loads(s) for s in splits]

    return splits


    # output_file = input_file.parents[0] / (input_file.name + ".rec.json") 

    # print("Writing to output file", output_file)

    # with open(output_file, "w") as f:
    #     json.dump(splits, f)