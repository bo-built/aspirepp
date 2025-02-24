from Lib.g_code_line import GCodeLine


if __name__ == '__main__':
    line = "G2 X=18.8750 Y=42.3125 Z=0.2500 I=18.8750 J=44.3125 V=9800 ;Outline Outer Circles - CW ARC"
    g_line = GCodeLine(line)
    import pdb
    pdb.set_trace()