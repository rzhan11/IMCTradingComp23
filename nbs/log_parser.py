import json
import sys
from pathlib import Path

def process_file(fname, start_sep, end_sep):

    input_file = Path(fname)

    print("Reading from input file", input_file)
    with open(input_file, "r") as f:
        text = f.read()
    
    text = unreduce_str(text)

    # split on start_sep
    splits = text.split(start_sep)

    # skip first entry (before __mark)
    splits = splits[1:]

    # split on end_sep
    splits = [s.split(end_sep) for s in splits]

    # # only keep before end_sep
    splits = [s[0] for s in splits]
    splits = [json.loads(s) for s in splits]



    return splits


def process_file_jasper(fname, start_sep, end_sep):

    input_file = Path(fname)

    print("Reading from input file", input_file)
    with open(input_file, "r") as f:
        lines = f.readlines()
        
    texts = []
    for line in lines:
        words = line.split(" ", 1)

        if words[0].startswith("{"):
            texts += [line]
        elif len(words) == 2:
            if words[1].startswith("{"):
                texts += [words[1]]

    text = "\n".join([json.loads(text)["logs"] for text in texts])

    # split on start_sep
    splits = text.split(start_sep)

    # skip first entry (before __mark)
    splits = splits[1:]

    # split on end_sep
    splits = [s.split(end_sep) for s in splits]

    # # only keep before end_sep
    splits = [s[0] for s in splits]
    splits = [json.loads(s) for s in splits]



    return splits



symbols = ["BANANAS", "PEARLS", "COCONUTS", "PINA_COLADAS", "BERRIES", "DIVING_GEAR", "BAGUETTE", "DIP", "UKULELE", "PICNIC_BASKET"]

def unreduce_str(s):
    unused_chars = "!@$^?~`" # add "%" if needed
    def get_unused_char(i):
        x = i // 10
        y = i % 10
        return unused_chars[x] + str(y)

    words = symbols + [
        "buy_orders", "sell_orders", 
        "price", "quantity", 
        "symbol", "product", "denomination",
    ]
    words.sort(key=lambda x:(len(x), x), reverse=True)

    convert_list = [ (sym, get_unused_char(i)) for i, sym in enumerate(words) ]
    print("convert", convert_list)
    
    for k, v in convert_list:
        s = s.replace(v, k)

    return s