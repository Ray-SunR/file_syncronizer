import os
import time
import json
from stat import *
from shutil import copy2, copytree

# The path you want to copy from
src_dir = "D:\\PDFTron"
src_json_name = "src_dir_tree.json"
dest_json_name = "dest_dir_tree.json"
# The path you want your difference file be
dest_dir = "C:\\Users\\Renchen\\Google Drive\\PDFTron"

ignore_list = ['D:\\PDFTron\\_DeveloperSandbox\\Aleksy\\node_server\\node_modules', 'D:\\PDFTron\\bin']

def GetDocLists(path):
    return os.listdir(path)

def CreateFileInfoJsonForDir(path):
    result = {}

    result['DirName'] = os.path.basename(path)
    result_tmp = {}
    result['Details']  = result_tmp
    result_tmp['Path'] = path
    result_tmp['Files'] = []
    result_tmp['SubDir'] = []
    if path in ignore_list:
        return result
    for file in GetDocLists(path):
        obj = {}
        if file.startswith('.'):
            continue
        filePath = os.path.join(path,file)
        stats = os.stat(filePath)
        children = {}
        #For Dir
        if(S_ISDIR(stats.st_mode)):
            children = CreateFileInfoJsonForDir(os.path.join(path,file))
            result_tmp['SubDir'].append(children)
        #For files
        else:
            obj['FileName'] = file
            obj_tmp = {}
            obj['Details'] = obj_tmp
            obj_tmp['CTime'] = stats.st_ctime
            obj_tmp['MTime'] = stats.st_mtime
            obj_tmp['CreatedTime'] = time.ctime(stats.st_ctime)
            obj_tmp['ModifiedTime'] = time.ctime(stats.st_mtime)
            result_tmp['Files'].append(obj)
    result_tmp['NumOfItems'] = len(result_tmp['SubDir']) + len(result_tmp['Files'])
    return result

def PrettyPrintJson(stuff):
    print json.dumps(stuff, sort_keys=True, indent=4, separators=(',',': '))

def DumpFileInfoToJson(result, dir, is_src):
    global src_json_name, dest_json_name
    if is_src:
        json_file_path = os.path.join(dir, src_json_name)
    else:
        json_file_path = os.path.join(dir, dest_json_name)

    with open(json_file_path, 'w') as f:
        f.write(json.dumps(result, sort_keys=True, indent=4, separators=(',',': ')))

def ReadFileInfoFromJson(fullpath):
    with open(fullpath, 'r') as f:
        return json.load(f)

def PopulateUpdateList(src_dir, dest_dir, result_stats):
    global src_json_name, dest_json_name
    src_json_full_path = os.path.join(src_dir, src_json_name)
    dest_json_full_path = os.path.join(dest_dir, dest_json_name)
    dest_dir_stats = {}
    # Should always update json file for src dir first
    src_dir_stats = CreateFileInfoJsonForDir(src_dir)
    DumpFileInfoToJson(src_dir_stats, src_dir, True)

    # Not necessary to update json file for the dest dir
    # because we may provide one already
    if os.path.exists(dest_json_full_path):
        dest_dir_stats = ReadFileInfoFromJson(dest_json_full_path)
    else:
        if not os.path.exists(dest_dir):
            os.mkdir(dest_dir)
        dest_dir_stats = CreateFileInfoJsonForDir(dest_dir)
        DumpFileInfoToJson(dest_dir_stats, dest_dir, False)
    PopulateUpdateListHelper(src_dir_stats['Details'], os.path.join(src_dir, src_dir_stats['DirName']), dest_dir_stats['Details'], os.path.join(dest_dir, dest_dir_stats['DirName']), result_stats)

def PopulateUpdateListWithBothJsons(src_dir, dest_dir, result_stats):
    global src_json_name, dest_json_name
    src_json_full_path = os.path.join(src_dir, src_json_name)
    dest_json_full_path = os.path.join(dest_dir, dest_json_name)
    src_dir_stats = ReadFileInfoFromJson(src_json_full_path)
    dest_dir_stats = ReadFileInfoFromJson(dest_json_full_path)

    PopulateUpdateListHelper(src_dir_stats['Details'], os.path.join(src_dir, src_dir_stats['DirName']), dest_dir_stats['Details'], os.path.join(dest_dir, dest_dir_stats['DirName']), result_stats)

def PopulateUpdateListHelper(src_details, src_dir, dest_details, dest_dir, result_stats):
    src_files = src_details['Files']
    dest_files = dest_details['Files']
    global ignore_list
    # For files
    for item in src_files:
        full_path = os.path.join(src_details['Path'], item['FileName'])
        if full_path in ignore_list:
            continue
        if not any(item['FileName'] == file['FileName'] for file in dest_files):
            result_stats.append(full_path)
        else:
           for file in dest_files:
               if file['FileName'] == item['FileName'] and file['Details']['MTime'] != item['Details']['MTime']:
                   result_stats.append(full_path)
                   break
               else:
                   continue

    # For dirs
    for item in src_details['SubDir']:
        if not item:
            continue
        full_path = os.path.join(src_details['Path'], item['DirName'])
        cond1 = True
        cond2 = False
        # If they share same common prefix in the ignore list
        # We have to dive into this dir and serialize one by one
        if any(os.path.commonprefix([full_path, ignore_dir]) for ignore_dir in ignore_list):
            cond1 = False
        cond2 = not any(item['DirName'] == dir['DirName'] for dir in dest_details['SubDir'])
        if cond1 and cond2:
            result_stats.append(full_path)
        else:
            if full_path in ignore_list:
                continue
            #Destination folder exists
            if dest_details['SubDir']:
                for dir in dest_details['SubDir']:
                    if dir['DirName'] == item['DirName']:
                        PopulateUpdateListHelper(item['Details'], os.path.join(src_dir, item['DirName']), dir['Details'], os.path.join(dest_dir, dir['DirName']), result_stats)
                    else:
                        continue
            #Destination folder does not exist
            else:
                for subFiles in item['Details']['Files']:
                    subfull_path = os.path.join(full_path, subFiles['FileName'])
                    if subfull_path in ignore_list:
                        continue
                    result_stats.append(subfull_path)
                for subDirs in item['Details']['SubDir']:
                    subfull_path = os.path.join(full_path, subDirs['DirName'])
                    if subfull_path in ignore_list:
                        continue
                    result_stats.append(subfull_path)

def CopyFilesIntoDestDir(ret, src_dir, dest_dir):
    for item in ret:
        if item in ignore_list:
            continue
        list = [item, src_dir]
        prefix = os.path.commonprefix(list)
        relPath = os.path.relpath(item, prefix)
        destFinalPath = os.path.join(dest_dir, relPath)
        if os.path.isfile(str(item)):
            print '[File]' + item + " Copied"
            if not os.path.exists(os.path.dirname(destFinalPath)):
                os.makedirs(os.path.dirname(destFinalPath))
            copy2(item, os.path.join(dest_dir, relPath))
        else:
            print '[Folder]' + item + " Copied"
            copytree(item, destFinalPath)

def CopyFilesIntoDestDirMain():
    global dest_dir, src_dir
    if not os.path.exists(dest_dir):
        os.mkdir(dest_dir)
    result_stats = []
    PopulateUpdateList(src_dir, dest_dir, result_stats)
    CopyFilesIntoDestDir(result_stats, src_dir, dest_dir)

def CopyFilesIntoDestDirMainWithBothJsonMain():
    global dest_dir, src_dir
    result_stats = []
    PopulateUpdateListWithBothJsons(src_dir, dest_dir, result_stats)
    CopyFilesIntoDestDir(result_stats, src_dir, dest_dir)

def CreateFileJsonInfoJsonForDirMain():
    global  dest_dir, src_dir
    src_result = CreateFileInfoJsonForDir(src_dir)
    dest_result = CreateFileInfoJsonForDir(dest_dir)

    DumpFileInfoToJson(src_result, src_dir, True)
    DumpFileInfoToJson(dest_result, dest_dir, False)

def CreateFileJsonInfoForDestDirMain():
    global dest_dir
    DumpFileInfoToJson(CreateFileInfoJsonForDir(dest_dir), dest_dir, False)

def CreateFileJsonInfoForSrcDirMain():
    global src_dir
    DumpFileInfoToJson(CreateFileInfoJsonForDir(src_dir), src_dir, True)

#CreateFileJsonInfoJsonForDirMain()
#CopyFilesIntoDestDirMain()
CopyFilesIntoDestDirMainWithBothJsonMain()
#CreateFileJsonInfoForDestDirMain()
#CreateFileJsonInfoForSrcDirMain()
