import os
import sys
import math
import time
import signal
import warnings
import argparse
import numpy as np

characters = {
    'Full': '.,-~:;=!*#$@', 
    'Half': '.~:=*#',
    'Solid': '░▒▓',
}
format = {
    'Blue': ['34'],
    'BrightBlue': ['1;34;1;94'],
    'Green': ['32']
}

# So we can do R| in help descriptions for line breaks while 
# maintaining smart formatting indents
class SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        SplitLines = argparse.HelpFormatter._split_lines
        split = text.split('R|')
        if len(split) > 1:
            count = True
            to_return = []
            # Each chunk split by R| we want to reformat
            for snip in split:
                # First one will not have R| in front so format normally
                if count: 
                    count = False; 
                    to_return.extend(SplitLines(self, snip, width))
                else:
                    to_return.extend(snip.splitlines())
            return to_return
        return SplitLines(self, text, width)
    
parser = argparse.ArgumentParser(formatter_class=SmartFormatter)

def format_options(d):
    return ''.join(f"\n'{i}'={v}" for i, v in d.items())

parser.add_argument("-w", "--width", help="Width of canvas. Default: terminal width")
parser.add_argument("-y", "--height", help="Height of the canvas. Default: terminal height")
parser.add_argument("-s", "--scale", help="Scale of the donut. Default: .75")
parser.add_argument("-1,", "--r1", "--radius1", "--minorRadius", help="Length of minor radius"
    "--radius of the cross-sectional circle")
parser.add_argument("-a", "--aspect", action="store_true", help="Respects aspect ratio if given none or only one width or height")
parser.add_argument("-2", "--r2", "--radius2", "--majorRadius", help="Length of the major radius"
    "--distance from center of torus to center of the cross-sectional circle")
parser.add_argument("-c", "--style", "--characters", help="Changes the characters used for the render. " \
"R|\nOptions: {}".format(format_options(characters)))
parser.add_argument("-i", "--format", "--colors", "--ansi", nargs='+', help="Sets the luminance format/colors according to the list of ansi codes " \
"provided from darkest to lightest. Do not use escape sequences. Simply type the codes like '1;31', for example, for bold, red foreground." \
"R|\nPresets: {}".format(format_options(format)))

args = parser.parse_args() 

output_format = ''
check = format.get(args.format[0])
if check: 
    output_format = check
elif len(args.format) > 0:
    output_format = args.format

print(output_format)

def set_if_args(v, other):
    i = vars(args)[v]
    return float(i) if i else other

theta_spacing = 0.07
phi_spacing = 0.02

R1 = set_if_args("r1", 1)
R2 = set_if_args("r2", 2)
K2 = 6

terminal_size  = os.get_terminal_size()
width = int(set_if_args("width", terminal_size.columns))
height = int(set_if_args("height", terminal_size.lines) - 1)

if (args.aspect):
    ideal_ratio = 4
    if (not args.width and not args.height) or (args.width and args.height):
        current_ratio = width / height
        if current_ratio > ideal_ratio:
            width = int(height * ideal_ratio)
        else:
            height = int(width / ideal_ratio)
    elif args.width:
        height = width // 4
    elif args.height:
        width = height * 4  
aspect_ratio = width / height * 1/2

scale = float(args.scale) if args.scale else .75
scale /= 10
K1 = scale*width*K2/((R1+R2))

chars = characters[args.style or 'Full']

def render_frame(A, B):
    cosA = math.cos(A)
    sinA = math.sin(A)
    cosB = math.cos(B)
    sinB = math.sin(B)

    output = [[' ' for _ in range(width)] for _ in range(height)]
    z_buffer = [[-float('inf') for _ in range(width)] for _ in range(height)]
    
    for theta in np.arange(0, 2*math.pi, theta_spacing):
        sin_theta, cos_theta = math.sin(theta), math.cos(theta)
        circleX = R2 + R1*cos_theta
        circleY = R1*sin_theta

        for phi in np.arange(0, 2*math.pi, phi_spacing):
            sin_phi, cos_phi = math.sin(phi), math.cos(phi)

            x = circleX*(cosB*cos_phi + sinA*sinB*sin_phi) - circleY*cosA*sinB
            y = circleX*(cos_phi*sinB - cosB*sinA*sin_phi) + circleY*cosA*cosB
            z = K2 + cosA*circleX*sin_phi + circleY*sinA
            if z <= 0: continue
            ooz = 1/z

            x_prime = round(width/2 + K1*ooz*x * aspect_ratio)
            y_prime = round(height/2 - K1*ooz*y)

            if 0 <= x_prime < width and 0 <= y_prime < height:
                luminance = (
                    cos_phi*cos_theta*sinB 
                    - cosA*cos_theta*sin_phi 
                    - sinA*sin_theta 
                    + cosB*(cosA*sin_theta - cos_theta*sinA*sin_phi)
                )

                if luminance > 0 and ooz > z_buffer[y_prime][x_prime]:
                    z_buffer[y_prime][x_prime] = ooz
                    def determine_index(list):
                        return list[min(int(luminance*len(list)), len(list)-1)]
                    char = determine_index(chars)
                    color = determine_index(output_format)
                    output[y_prime][x_prime] = f"\033[{color}m{char}\033[0m"

    for row in output:
        print(f"".join(row))

A = B = 0
def signal_handler(_, __):
    render_frame(A, B)
    warnings.filterwarnings("ignore")
    sys.exit()


signal.signal(signal.SIGINT, signal_handler)

framerate = 10
interval = 1/framerate
speedA = speedB = 2*math.pi/ 200
while True:
    render_frame(A, B)
    print(f"\x1b[{height}A", end="")
    A += speedA
    B += speedB
    time.sleep(interval)
