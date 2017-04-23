__author__ = "aycruzp,rjzawis"
__version = '1.13'
 
##############################################################################################################
# This application is used to test OpenShift Origin cartridges.                                              #
#                                                                                                            #
# It will remotely pull cartridges and created, log, and delete them.                                        #
#                                                                                                            #
# I will also manipulate some files and push it to the server. Then verify the changes were made succesfully.#
##############################################################################################################
 
import time
import os
import threading
import argparse
import re
import fnmatch
import requests 
from shutil import move
from prettytable import PrettyTable
from subprocess import Popen, PIPE, STDOUT, call
from tempfile import NamedTemporaryFile, mkstemp
from uuid import uuid4
 
 
""" display the server the script is running against """
def display_oso_server():
    print("")
    cmd = Popen(["rhc","servers"], stdout=PIPE, stderr=STDOUT)
    out, err = cmd.communicate()
    lines = out.splitlines()
    idx = 0
    for line in lines:
        if line.__contains__("(in use)"):
            print("")
            print("Script running against OSO Server : ")
            print lines[idx + 2]
            print("    Domain:        " + STR_TEST_DOMAIN)
        else:
            idx += 1
    print color
    ''' raise SystemExit(0) '''

 
""" Create domain for the testing apps. """
def create_test_domain():
    cmd = Popen(["rhc", "domain", "create", STR_TEST_DOMAIN], stdout=PIPE, stderr=STDOUT)
    out, err = cmd.communicate()
    if out.__contains__("Creating domain"):
        print "Creating domain [" + STR_TEST_DOMAIN + "]... " + green + "done" + color
    else:
        print red + out + color
 
 
""" Get User Info """
def get_rhc_account_info():
    global user_id
    global server
    cmd = Popen(["rhc","account"], stdout=PIPE, stderr=STDOUT)
    out, err = cmd.communicate()
    lines = out.splitlines()
    server = lines[0].split(" ")[-1]
    """ print lines """
    for line in lines:
        if line.__contains__("ID"):
            user_id = line.split()[-1]
        elif line.__contains__("Gear Sizes"):
            gears = list(line.strip().partition(':')[-1].split())
    return gears
 
 
""" Get Region Info """
def get_rhc_region_info():
    cmd = Popen(["rhc","regions"], stdout=PIPE, stderr=STDOUT)
    out, err = cmd.communicate()
    lines = out.splitlines()
    lines = ['Server blah-aio01.dudeshift.partshop.lab24.co', ' ', "Region 'georgia' (uuid: 567...)", '------', '    Available Zones : G-DEV_INT-nsag-z1-c1', ' ', "Region 'texas' (uuid: 890...)", '------', '    Available Zones : T-DEV_INT-nsat-z3-c1']
    """ print lines """
    server = lines[0].split(" ")[-1]
    regions = []
    regions.append('')
    for line in lines:
        """ print line """
        if line.__contains__("Region '"):
            idx1 = line.find('\'', 0, len(line))
            idx2 = line.rfind('\'', idx1, len(line))
            rgn = line[idx1+1:idx2]
            """ print rgn """
            regions.append(rgn)
    return regions
 
 
""" Get list of web cartridges available. """
def get_web_cartridges():
    web_cartridges = []
    cmd = Popen(["rhc", "cartridges"], stdout=PIPE, stderr=STDOUT)
    out, err = cmd.communicate()
    raw_resp = out.splitlines()
    for cartridge in raw_resp:
        if cartridge.endswith('web'):
            web_cartridges.append(cartridge.rsplit()[0])
            if args.verbose:
                print "......" + cartridge
    print "  "
    return web_cartridges
 
 
""" Get list of addon cartridges available. """
"""     skip over broken Mongo 10gen monitoring Service agent and HAProxy addons """
def get_addon_cartridges():
    addon_cartridges = []
    addon_cartridges.append('')
    cmd = Popen(["rhc", "cartridges"], stdout=PIPE, stderr=STDOUT)
    out, err = cmd.communicate()
    raw_resp = out.splitlines()
    for cartridge in raw_resp:
        if cartridge.endswith('addon'):
            addon_cartridges.append(cartridge.rsplit()[0])
            if args.verbose:
                print "......" + cartridge
    print "  "
    """ raise SystemExit(0)"""
    addon_cartridges.remove("10gen-mms-agent-0.1")
    addon_cartridges.remove("haproxy-1.4")
    return addon_cartridges
 

""" Exclude some cartridges from the list.
This is useful if one or more cartridges are broken.
"""
def exclude_cartridges(web_cartridges, exclude):
    for cartridge in exclude:
        web_cartridges.remove(cartridge)
    return web_cartridges
 
 
""" create all the apps"""
def create_apps(regions, web_carts, addon_carts, gears, temp):
    total_web_carts = len(web_carts)
    start_time = time.time()
    threads = []

    scaling_options = ["--no-scaling", "--scaling"]
    addon_carts = ['', 'cron-1.4', 'jenkins-client-1']
    total_addon_carts = len(addon_carts)
    """ db_carts = ['', 'mongodb-2.4', 'mysql-5.1', 'mysql-5.5', 'phpmyadmin-4', 'postgresql-8.4', 'postgresql-9.2'] """
    db_carts = ['', 'mongodb-2.4', 'mysql-5.1', 'mysql-5.1 phpmyadmin-4', 'mysql-5.5', 'mysql-5.5 phpmyadmin-4', 'postgresql-8.4', 'postgresql-9.2']
    total_db_carts = len(db_carts)
    num_apps = 0
    print "Creating web app[s] : "
    regions = ['']
    for rgn in regions:
        for gear in gears:
            for scaling in scaling_options:
                for i in range(total_web_carts):
                    for j in range(total_addon_carts):
                        for k in range(total_db_carts):
                            if (("--scaling" in scaling) and ("diy" in web_carts[i])):
                                print "....skipping over DIY carts - they can't be scaled"
                            else :
                                num_apps += 1
                                create_app(num_apps, rgn.strip(), web_carts[i], addon_carts[j], db_carts[k], gear.strip(), scaling, temp)
                                print "....sleeping...{0} s".format(INT_THREAD_SLEEP_SECS)
                                time.sleep(15)
                                """
                                t = threading.Thread(target=create_app, args=(num_apps, rgn.strip(), web_carts[i], addon_carts[j], db_carts[k], gear.strip(), scaling, temp))
                                threads.append(t)
    for i in range(len(threads)):
        print ".........starting thread {0}...".format(i+1) + " of {0}".format(len(threads))
        threads[i].start()
        time.sleep(INT_THREAD_SLEEP_SECS)
    for i in range(len(threads)):
        threads[i].join()
    """
    print " "
    print "Finished creation app process ...created {0}".format(num_apps) + " apps."
    print "Ran creation app test in {0} s".format(time.time() - start_time)
 
 
""" Create web apps with specific gear and specific cartridge. """
def create_app(app_num, rgn, web, db, addon, gear, scaling, temp):
    """
    w = web.replace('.', '').replace('-', '')
    d = db.replace('.', '').replace('-', '')
    a = addon.replace('.', '').replace('-', '')
    s = "y"
    if scaling.__contains__("no"):
        s = "n"
    """
    g = gear.replace(',', '')
    """ app = w + d + a + s + g[0] """
    app = "app" + str(app_num)
    if (len(rgn.strip()) == 0):
        str_rgn = ""
    else:
        str_rgn = "--region " + rgn.strip()
    if ( (addon.__contains__("mysql")) and (addon.__contains__("phpmyad"))):
        words = addon.split(" ",addon.count(" "))
        addon1 = words[0]
        addon2 = words[1]
        print "....[1] rhc create-app " + app + " " + web + " " + db + " " + addon1 + " " + addon2 + " " + scaling + " " + git + " " + dns + " -g " + g  + " -n " + STR_TEST_DOMAIN + str_rgn + " &"
        cmd = Popen(['rhc', 'create-app', app, web, db, addon1, addon2, scaling, git, dns, '-g', g, '-n', STR_TEST_DOMAIN, str_rgn], stdout=PIPE, stderr=STDOUT)
    else:
        print "....[2] rhc create-app " + app + " " + web + " " + db + " " + addon + " " + scaling + " " + git + " " + dns + " -g " + g  + " -n " + STR_TEST_DOMAIN + str_rgn + " &"
        cmd = Popen(['rhc', 'create-app', app, web, db, addon, scaling, git, dns, '-g', g, '-n', STR_TEST_DOMAIN, str_rgn], stdout=PIPE, stderr=STDOUT)
    out, err = cmd.communicate()
    if not args.verbose:
        if out.find("done") is not -1:
            print "........'{0}' ... ".format(app) + green + "done" + color
        elif out.find("already") is not -1:
            print yellow + "The supplied application name '{0}' already exists.".format(app) + color
        else:
            print yellow + out + color
    else:
        print out
    temp.write(out)

 
""" Get a list of current applications deployed. """
def get_my_apps(gears, web_cartridges_names):
    apps_id = []
    result = {}
    row = []
    app_info = []
    myapps = []
    global myurls
    cmd = Popen(["rhc","domain-show", STR_TEST_DOMAIN], stdout=PIPE,stderr=STDOUT)
    out, err = cmd.communicate()
    tabledef = PrettyTable()
    tabheader = ["Cartridge"]
    tabheader.extend(gears)
    tabledef._set_field_names(tabheader)
    for line in out.splitlines():
        print line
        if line.find("uuid") is not -1:
            print line
            row.append(line.split()[0])       # Name of application
            row.append(line.split()[-1])      # UUID of the application.
            myurls.append(line.split()[2])    # URL of application
            gear = re.match("\w+test(.+)", line.split()[0])
            #gear.group(1)
        else:
            continue

    for app in range(len(row)):
        if app % 2 == 0:
            myapps.append(row[app])

    for cartridge in web_cartridges_names:
        result = []
        result.append(cartridge)
        for gear in gears:
            if myapps.__contains__("{0}utest{1}".format(cartridge.replace('.',"").replace('-',""),gear.replace(',',''))):
                result.append(green + "done" + color)
            else:
                result.append(red + "failed" + color)
        tabledef.add_row(result)

    print ""
    print tabledef.get_string()
    return myapps
 
 
""" Find, replace and push into the repository a specific change in a file. This is only for testing. """
def automation_git(file,temp):
    matches = []
    dir = os.path.expanduser('~') + STR_TEST_DIR
    for dirName, subdirList, fileList in os.walk(dir):
        """ changed this to *. cuz each app git repo has an 'index' file that was causing an unnecessary match """
        for filename in fnmatch.filter(fileList, file + ".*"):
            matches.append(os.path.join(dirName,filename))
    print("")
    global myapps
    if len(matches):
        print "Modifying landing page and pushing code to server for : [git add / commit / push]"
        for match in matches:
            for app in myapps:
                if match.__contains__(app):
                    print "..........",match,app
                    os.chdir(os.path.expanduser('~') + STR_TEST_DIR + app )
                    replace(match, "Welcome", "Welcome my name is -> {0}!".format(app))
                    cmd = Popen(["git", "add", "."], stdout = PIPE, stderr = STDOUT)
                    out,err = cmd.communicate()
                    cmd = Popen(["git", "commit", "-m", "\"Automation testing script\""], stdout = PIPE, stderr = STDOUT)
                    out,err = cmd.communicate()
                    cmd = Popen(["git", "push"], stdout = PIPE, stderr = STDOUT)
                    out,err = cmd.communicate()
                    if err is None:
                        for line in out.splitlines():
                            if line.find("remote:") is not -1:
                                if args.verbose:
                                    print line
                                temp.write(line)
 
 
""" Replace word in the landing page to test cartridge. """
def replace(file_path, pattern, subst):
    fh, abs_path = mkstemp()
    with open(abs_path, 'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                new_file.write(line.replace(pattern,subst))
    os.close(fh)
    os.remove(file_path)
    move(abs_path, file_path)
 
 
""" Hit the url of each app.
This function makes sure that every app is reachable.
"""
def hit_apps():
    tabledef = PrettyTable()
    tabheader = []
    tabheader.append("Application")
    tabheader.append("Status")
    tabheader.append("Modify/Git/Verify")
    tabledef._set_field_names(tabheader)
    results = []
    col_values = []
    """ establish a single session so that the multiple s.gets below reuse existing connection """
    s = requests.Session()
    ''' print "Calling s=requests.Session() to establish a single TCP connection to reuse" '''
    print "Attempting to reach : requests.Session().get(app)"
    for app in myurls:
        if app.find("jenkins1") is -1: 
            print "..........{0}".format(app)
            response = s.get(app)
            results.append(app.split('//')[1].split('-')[0])
            if response.status_code is not 200:
                status = red + str(response.status_code) + color
            else:
                status = green + str(response.status_code) + color
            results.append(status)
            found = re.search("({0})".format(app.split('//')[1].split('-')[0]), response.content)
            if found:
                results.append(green + "Pass" + color)
            else:
                results.append(red + "Failed" + color)
        else:
            print "..........skipping Jenkins Server"
            results.append(app.split('//')[1].split('-')[0])
            status = red + "Skipped" + color
            results.append(status)
            results.append(red + "Skipped" + color)
    index = 0
    for app in range(len(myurls)):
        tabledef.add_row([results[index],results[index+1],results[index+2]])
        index = index + 3
    print tabledef.get_string()
 

""" Start deleting all apps created by the script. """
def start_deletion(apps, temp):
    start_time = time.time()
    threads = []
    print "Deleting application[s] : [rhc app delete...]"
    for app in apps:
        t = threading.Thread(target=delete_app, args=(app, temp, ))
        threads.append(t)
    for i in range(len(threads)):
        threads[i].start()
    for i in range(len(threads)):
        threads[i].join()
    print "Finished deleting apps from server ..."
    print "Ran deletion app test in {0}s".format(time.time() - start_time)
 

""" Delete application from server. """
""" use API instead of rhc - we think it's quicker """
""" curl -k -X DELETE https://blah-aio01.dudeshift.partshop.lab24.co/broker/rest/domain/osov4test/application/diy01ns -u "demo:demo """
def delete_app(app, temp):
    resp = Popen(["rhc","app","delete", app, "--confirm", '-n', STR_TEST_DOMAIN], stdout=PIPE, stderr=STDOUT)
    out, err = resp.communicate()
    if not args.verbose:
        if out.find("deleted") is not -1:
            print "........'{0}' ... ".format(app) + green + "deleted" + color
        else:
            print yellow + out + color
    else:
        print out
    temp.write(out)
 
 
""" Delete the domain created at the beginning of the script """
def destroy_test_domain():
    cmd = Popen(["rhc", "domain","delete", STR_TEST_DOMAIN], stdout=PIPE, stderr=STDOUT)
    out, err = cmd.communicate()
    if out.__contains__("deleted"):
        print "Deleting domain [" + STR_TEST_DOMAIN + "]... " + green + "done" + color
    else:
        print red + out + color
 
 
def main():
    global myapps
    global myurls
    global args
    global red
    global green
    global yellow
    global color
    global dns
    global git
    global STR_TEST_DIR
    global STR_TEST_DOMAIN
    global INT_THREAD_SLEEP_SECS

    color = '\033[1;m'
    red = '\033[1;31m'
    green = '\033[1;32m'
    yellow = '\033[1;33m'

    STR_TEST_DOMAIN = "osov4test"
    STR_TEST_DIR = "/oso-tests/"
    INT_THREAD_SLEEP_SECS = 10

    """ clear the screen """
    os.system('clear')

    parser = argparse.ArgumentParser(description="")
    parser.add_argument('-e','--exclude', nargs="*", help = 'exclude broken cartridges')
    parser.add_argument('-o','--out', action='store_true', help = 'save output in a log file')
    parser.add_argument('-v','--verbose', action='store_true', help = 'Verbose mode. Causes ssh to print debuggin messages about its progress.')
    parser.add_argument('--no-git', action='store_true', help = 'skip creating the local Git repository')
    parser.add_argument('--no-dns', action='store_true', help = 'skip waiting for the application DNS name to resolve. Must be used in combination with --no-git')
    parser.add_argument('-f', '--full', action='store_true', help = 'enable the functionality of pulling, modifying and pushing the code.')
    args = parser.parse_args()

    certs_path = True
    key_path = os.path.expanduser('~') + '/.ssh/'
    temp = NamedTemporaryFile(mode="w+t", delete = not args.out)
    temp_name = temp.name.split('/')[2]

    start_time = time.time()

    if args.no_dns is True and args.no_git is True:
        dns = "--no-dns"
        git = "--no-git"
    elif args.no_git is True:
        git = "--no-git"
        dns = ""
    else:
        git = ""
        dns = ""


    print "Start the automated test process"
    display_oso_server()


    print "\nCreate the test domain [" + STR_TEST_DOMAIN +"]... [rhc domain create]"
    create_test_domain()


    print "\nGet web cartridge info... [rhc cartridges grep web]"
    web_cartridge_names = get_web_cartridges()
    if args.exclude is not None:
        web_cartridge_names = exclude_cartridges(web_cartridge_names,args.exlude)
    print web_cartridge_names


    print "\nGet addon cartridge info... [rhc cartridges grep addon]"
    addon_cartridge_names = get_addon_cartridges()
    if args.exclude is not None:
        addon_cartridge_names = exclude_cartridges(addon_cartridge_names
                                                  ,args.exlude)
    print addon_cartridge_names


    print "\nGet gear sizes ... [rhc account]"
    gears = get_rhc_account_info()
    print gears


    print "\nGet the regions ... [rhc regions]"
    regions = get_rhc_region_info()
    print regions

    """
    print "\nCreate a Jenkins Server"
    if not os.path.isdir(os.path.expanduser('~') + STR_TEST_DIR):
        os.mkdir(os.path.expanduser('~')  + STR_TEST_DIR)
    os.chdir(os.path.expanduser('~') + STR_TEST_DIR)
    print "rhc create-app jenkins jenkins-1 --no-git -n " + STR_TEST_DOMAIN
    cmd = Popen(['rhc', 'create-app', 'jenkins', 'jenkins-1', '--no-git', '-n', STR_TEST_DOMAIN], stdout=PIPE, stderr=STDOUT)
    out, err = cmd.communicate()
    if not args.verbose:
        if out.find("done") is not -1:
            print "........'{0}' ... ".format("jenkins") + green + "done" + color
        elif out.find("already") is not -1:
            print yellow + "The supplied application name '{0}' already exists.".format(app) + color
        else:
            print yellow + out + color
    else:
        print out
    temp.write(out)
    """

    """
    exclude the jenkins-1 web cartridge from further processing - there can only be 1
    """
    print "\nOnly 1 Jenkins server can exist per domain, removing cartridge from our processing list"
    web_cartridge_names.remove("jenkins-1")


    print "\nCreating the rest of the web app[s] ... [rhc create-app]"
    if not os.path.isdir(os.path.expanduser('~') + STR_TEST_DIR):
        os.mkdir(os.path.expanduser('~')  + STR_TEST_DIR)
    os.chdir(os.path.expanduser('~') + STR_TEST_DIR)
    create_apps(regions, web_cartridge_names, addon_cartridge_names, gears, temp)


    raise SystemExit(0)


    print "\nGet created app[s] info ... [rhc domain-show]"
    myapps = []
    myurls = []
    myapps = get_my_apps(gears, web_cartridge_names)

    if args.full is True:
        if args.no_git is False:
            automation_git("index",temp)        # Most applications index.* file
            automation_git("config",temp)       # Ruby Application
            automation_git("wsgi",temp)         # Python Applications OSO v4
            automation_git("application",temp)  # Python Applications OSO v3 high side
            hit_apps()

    ans = raw_input("\nDo you want to delete the created test apps and environment ? (y/n) ")
    if ans is 'Y' or ans is 'y':
        print "Destroying test environment ... [rhc app, domain delete]"
        start_deletion(myapps, temp)
        destroy_test_domain()
        print "Deleting local folder : " + os.path.expanduser('~') + STR_TEST_DIR
        os.system("rm -rf " + os.path.expanduser('~') + STR_TEST_DIR)

    print "\nRan test in {0}s".format(time.time()-start_time)

if __name__ == '__main__':
    main()

