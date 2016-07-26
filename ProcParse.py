#!/usr/bin/env python
# Written for Python 2.5.7 by Pete Mueller in March 2016
import sys
import readline  # probably not needed
import subprocess
from subprocess import PIPE, STDOUT
import shlex
import time

availOptions = {'check':'Eliminates user prompts to produce a full listing and performs additional checks',
                'checkType':'As above but limits output to test title and type',
                'manual':'Suppresses all built in automation',
                'purpose':'Prints only purposes with performance constraints ("seconds" in description)',
                'performance':'Lists the procedures that are excluded from the test list',
                'titles':'Checks for presences of supplied list of titles in procedure',
                'nolog' : 'Disable log to file'}

romanNumerals = ['Nil', 'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', 'xi', 'xii', 'xiii', 'xiv']
shellCommands = {'WiFi Dial':"egrep -m 1 \"RwConnection: voip\-.*: onStateChanged\(DIALING\)\"",
                 'Cell Dial':"egrep -m 1 \"RwConnection: cell\-.*: onStateChanged\(DIALING\)\"",
                 'Call Alerting':"grep -m 1 \"setCallState NEW -> RINGING\"",
                 'Resume Call':"grep -m 1 \"setCallState ACTIVE -> ACTIVE\"",
                 'Active Call Ended':"grep -m 1 \"setCallState ACTIVE -> DISCONNECTED\"",
                 'Call Not Delivered':"grep -m 1 \"setCallState RINGING -> DISCONNECTED\"",
                 'Call Termination':"grep -m 1 \"setCallState ACTIVE -> DISCONNECTED\"",
                 'Hold Call':"grep -m 1 \"setCallState ACTIVE -> ON_HOLD\"",
                 'WiFi Call Incoming':"egrep -m 1 \"RwConnection: voip\-.*: onStateChanged\(RINGING)\)\"",
                 'Cell Call Incoming':"egrep -m 1 \"RwConnection: cell\-.*: onStateChanged\(RINGING\)\"",
                 'Cell Handover':"egrep -m 1 \"RwConnection: prxy\-.*: handover successful!\"",
                 'WiFi Handover':"egrep -m 1 \"RwConnection: prxy\-.*: handover successful!\"",
                 'Rapid Handover':"grep \"initiating handover to \"",
                 '3 Topic Subscription':"grep -m 3 \"subscribing to topic\"",
                 '5 Topic Subscription':"grep -m 5 \"subscribing to topic\"",
                 'SIP Registration Req':"egrep \"SipSessionImpl: CSeq: .* REGISTER\"",
                 'DTMF Failure':"grep \"failed to queue DTMF\"",
                 'UF SMS':"egrep -m 1 \"MessagingApi: incoming SMS \'\(#.*\) You received a new message from .*\"",
                 'UF SMS ID Text':"grep -m 1 \"UF SMS ID\"",
                 'GCM Wakeup':"egrep -m 1 \"gcm message received from .*\: \{\"protocol\"\:\"mqtt\"\}\"",
                 'MQTT Connect':"grep -m 1 \"MSG_SERVER_IS_CONNECTED\"",
                 'MQTT Disconnect':"grep -m 1 \"disconnecting from mqtt\"",
                 'Cell Connectivity':"grep -m 1 \"network connectivity changed: MOBILE_CONNECTED\"",
                 'MQTT Continuous Retry':"grep -m 10 \"retrying mqtt connect in \"",
                 'MQTT Five Retry':"grep -m 5 \"retrying mqtt connect in \"",
                 'MQTT Cell Retry':"grep -m 1 \"NetworkAgentInfo \[MOBILE (LTE)\"",
                 'MQTT WiFi Restoration':"egrep -m 1 \"\[WIFI \(\) - .*\] validation  passed\"",
                 'MQTT WiFi Reevaluation':"grep -m 2 \"Forcing reevaluation\"",
                 'MQTT Cell Restoration':"grep -m 3 \"setProvNotificationVisibleIntent null visible=false networkType=MOBILE\"",
                 'S3 Handshake Exception':"grep -m 1 \"SSLHandshakeException\"",
                 'UF SMS Voicemail':"egrep -m 1 \"incoming SMS \'\(#.*\) You received a new voicemail.\"",
                 'UF SMS Voicemail Suppression':"egrep -m 1 \"hiding system PDU \(\(\#.*\) You received a new voicemail.\"",
                 'Idle Mode':"adb shell input keyevent 26;adb shell input keyevent 26;adb shell dumpsys battery unplug;adb shell dumpsys deviceidle step;adb shell dumpsys deviceidle step;adb shell dumpsys deviceidle step;adb shell dumpsys deviceidle step",
                 'Active Mode':"shell dumpsys deviceidle step"
                 }

shellEvents = {'RepublicFramework':"RwConnection",
               'CallsManager':"CallsManager",
               'Handover':"initiating handover 10",
               'Subscription':"subscription",
               'SipSessionImpl Event':"SipSessionImpl",
               'Idle Forced':"Now forced in to idle mode",
               'Step Active':"Stepped to: ACTIVE",
               'HandleSendDtmf':'HandleSendDtmf',
               'MessagingApi':'MessagingApi',
               'MqttClient':'MqttClient',
               'RwSdk':'RwSdk',
               'MqttConnectionAttemptController':'MqttConnectionAttemptController',
               'ConnectivityService':'ConnectivityService',
               'NetworkMonitor/NetworkAgentInfo':'NetworkMonitor/NetworkAgentInfo',
               'UploadS3Task':'UploadS3Task',
               'RwCarrierMessagingService':'RwCarrierMessagingService'
               }

def waitForUSBConnection():
    # Create logcat process and run to pipe
    print '\n\n\n\n\n\nChecking device connectivity by issuing "adb logcat -c"'
    print 'Connectivity issue is present if this message does not scroll up.'
    print 'To resolve:'
    print 'Ensure DUT is connected to the USB and USB is connected to host computer.'
    print 'Ensure that no other device (such as the RMD) is also connected to USB.'
    print 'Ensure DUT is in debug mode: Open settings, select about phone and tap build number 7 times.'
    print '                             Go back to settings, select Developer options and activate USB debugging.'
    print '                             Select checkbox (if present) on resulting toast and acknowledge.'
    print 'It may also be necessary to unlock the DUT display.'
    
    line=subprocess.check_output(shlex.split("adb logcat -c"))
    print '\n\n\n\n\n\n\n\n'
    return

def adbShellCommand(command, subcommand, state):
    print '        ISSUING '+command+' '+subcommand+' '+state
    return subprocess.check_output(['adb', 'shell', command, subcommand, state])

def adbServiceChange(interface, state):
    adbShellCommand('svc', interface, state)
    return

def setIdleMode():
    subprocess.check_output(['adb', 'shell', 'dumpsys', 'battery', 'unplug'])
    presentState=subprocess.check_output(['adb', 'shell', 'dumpsys', 'deviceidle', 'step'])
    if 'ACTIVE' in presentState:
        subprocess.check_output(['adb', 'shell', 'input', 'keyevent', '26'])
        subprocess.check_output(['adb', 'shell', 'dumpsys', 'battery', 'unplug'])
    while not('IDLE' in presentState) or '_' in presentState:
            presentState=subprocess.check_output(['adb', 'shell', 'dumpsys', 'deviceidle', 'step'])
    print '        '+presentState
    return
    

# 'Consumes' lines of no interest up to and including target string but saves the last test title seen
def skipLines(file, target, option):
    line = " "
    testTitle = "Test Title"
    testType = "Unknown"
    while not(target in line) and line != "":
        lastLine = line  # save the last line read because the test title has no unique identifier but is followed by 'Definition...' 
        line = file.readline()
        if 'Definition and applicability' in line:
            testTitle = lastLine
        if 'Test type:' in line:
            testType = line.split(': ')[1]
    if line == "":
        return False
    else:
        if 'check' in option:
            testTitle = testTitle+'Test Type: '+testType
        return testTitle

# Print all purposes or just performance ones
def printPurposes(file, test, option):
    line = ' '
    # file is reopened each time this is called so find the test each time
    while not('REQ'+test+'.' in line) and line!="":
        line = file.readline()
    if line == "" and not('performance' in option):
        print 'TEST '+test+'. NOT FOUND IN PROCEDURE'
        raw_input()
    else:
        # print 'EOF not reached'
        while not('Initial Conditions' in line) and line!="":
            if '[REQ' in line:
                if not('performance' in option) or ('seconds' in line): print line,
            line = file.readline()
    return
    
# With file pointer presently at start of number list, reads full list into list variable provided.
# This WILL 'consume' the nextHeading line but not include it in the returned list.
def buildList(file, list, nextHeading):
    line=file.readline()
    while not(nextHeading in line) and line != "":
        list.append(line)
        line = file.readline()
    if line == "": return False
    else: return True

# Print requirement step, prompt user to confirm and perform actions if supported.
def processRequirementStep(line, reqCount, startTime, option):
    print "    "+romanNumerals[reqCount]+'. '+str(line.split('. ')[1]),
    if 'Shell Command' in line and not('check' in option):
        raw_input('        PRESS RETURN TO PERFORM SHELL COMMAND CHECK.')
        # close file for write, open for read, check for expected contents and inform tester
        shellOutFile = open('shell_out.txt','r')
        logLine = shellOutFile.readline()
        print '        DUT Response: '+logLine
        shellOutFile.close()
        if 'Events' in line:
            checkString = shellEvents[line.split(' Events')[0].split('Confirm ')[1].split(' ')[1]]
            targetOccurances = int(line.split(' Events')[0].split('Confirm ')[1].split(' ')[0])
            occurances = 0
            while logLine != '':
                if checkString in logLine: occurances += 1
                logLine = shellOutFile.readline()
                print '        DUT Response: '+logLine
            if occurances != targetOccurances:
                print '        OCCURANCE OF '+checkString+' EVENTS ('+str(occurances)+' DOES NOT MATCH EXPECTATION ('+str(targetOccurances)+')'
            else:
                print '        OCCURANCE OF '+checkString+' EVENTS ('+str(occurances)+' MATCHED EXPECTATION ('+str(targetOccurances)+')'
        else:                        
            checkString = shellEvents[line.split(' Event')[0].split(' the ')[1]]
            if checkString in logLine:
                print '        '+checkString+' event CONFIRMED.'
            else:
                print '        '+checkString+' event FAILED!!!'
    elif 'seconds' in line:
        if not('check' in option):
            raw_input('        PRESS RETURN TO RECORD TIME OF OBSERVED EVENT')
        elapsedTime=int(time.time()-startTime)
        print '        ELAPSED TIME: '+str(int(elapsedTime)),
        if 'within' in line:
            spec=int(line.split(' seconds')[0].split('within ')[1])
            if elapsedTime>spec:
                print '        ***FAIL***  Spec='+str(spec)
            else:
                print '        ***PASS***  Spec='+str(spec)
    elif not('check' in option):
        raw_input()
    return

# Pretty print procedure steps fixing the list numbers and perform actions if supported
def processProcedureStep(testId, proc, option):
    lineCounter = 1 # Next test number is indistinguishable from end of procedure so exclude it
    procCount = 0
    reqCount = 0
    startTime = 0


    for line in proc:
        if not(lineCounter==len(proc)):  # Check that end of file was not reached
            stepNum=line.split('.')[0]
            if '      ' in line.split('.')[0]:        # If indented 6 spaces then this is a requirement so change to roman numeral and indent
                reqCount += 1
                processRequirementStep(line, reqCount, startTime, option)
            elif '   1.' in line and lineCounter==len(proc)-1:  # Handle start of new section
                pass
            else:
                procCount += 1
                reqCount = 0
                print str(procCount)+'. '+str(line.split('. ')[1]),
                if 'Turn off the display and place the DUT into Idle Mode' in line:
                    setIdleMode()
                elif 'Shell Command' in line and not('check' in option):
                    if 'Abort' in line:
                        shellLogcatPipe.terminate()
                    else:
                        # build strings for shell commands and then properly fomated lists same
                        logString = 'adb logcat'
                        if ('Check' in line):
                            grepString = shellCommands[line.split(' Check')[0].split(' the ')[1]]
                            print '        ISSUING: '+logString+' | '+grepString
                            logCommand = shlex.split(logString)
                            grepCommand = shlex.split(grepString)

                            # Create logcat process and run to pipe
                            shellLogcatPipe = subprocess.Popen(logCommand,stdout=PIPE)

                            # Open output file, trigger process to write to it and close
                            shellOutFile = open('shell_out.txt', 'w+')
                            subprocess.Popen(grepCommand,stdin=shellLogcatPipe.stdout,stderr=STDOUT,stdout=shellOutFile)
                            shellOutFile.close()
                        elif ('Set' in line):
                            grepString = 'adb '+shellCommands[line.split(' Set')[0].split(' the ')[1]]
                            print '        ISSUING: '+grepString
                            grepCommand = shlex.split(grepString)

                            # Open output file, trigger process to write to it and close
                            shellOutFile = open('shell_out.txt', 'w+')
                            subprocess.Popen(grepCommand,stderr=STDOUT,stdout=shellOutFile)
                            shellOutFile.close()
                elif 'test timer' in line:
                    if not('check' in option): raw_input('        PRESS RETURN TO START TIMER')
                    startTime = time.time()
                elif 'estart timer' in line:
                    if not('check' in option): raw_input('        PRESS RETURN TO RESTART TIMER')
                    startTime = time.time()
                elif 'Wait ' in line and not('check' in option):
                    if 'second' in line:
                        wait=(float)(line.split(' second')[0].split('Wait ')[1])
                        print '        WAITING '+str(wait)+' seconds...'
                        time.sleep(wait)
                    elif 'minute' in line:
                        wait=(float)(line.split(' minute')[0].split('Wait ')[1])
                        print '        WAITING '+str(wait)+'minutes...'
                        time.sleep(wait)
                elif 'Disable Cell Data' in line:
                    adbServiceChange('data', 'disable')
                elif 'Select the WiFi icon on the Common Settings screen to disable WiFi on the DUT' in line:
                    adbServiceChange('wifi', 'disable')                    
                elif 'Enable Cell Data' in line:
                    adbServiceChange('data', 'enable')                    
                elif 'Select the WiFi icon on the Common Settings screen to enable WiFi on the DUT' in line:
                    adbServiceChange('wifi', 'enable')                    
        lineCounter += 1
    return
    
def parseByTest(file, test, option):
    initialCondList = []
    procedureList = []
    returnCode = False

    if ('purpose' in option) or ('performance' in option): printPurposes(file, test, option)
    else:
        # Find first test number in requirements lines
        testTitle = skipLines(file, 'REQ'+test+'.', option)    
        if testTitle:
            if not ('check' in option):
                print ('\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n')
            print('\n\nTest case: '+test+' - '+testTitle.split('1. ')[1]),
            # Clear logcat buffer and read to a file to capture test session
            if not('check' in option or 'nolog' in option):
                logcatOutFilename = 'logs/logcat'+test+'.txt'
                logcatOutFile = open(logcatOutFilename, 'w')
                subprocess.Popen(shlex.split("adb logcat -c"))
                subprocess.Popen(shlex.split("adb logcat"),stdout=logcatOutFile)
                print '        LOGCAT WRITING TO '+logcatOutFilename+'.  PLEASE POST ON FAILURE.'

                propertiesFilename = 'devProp'+'.txt'
                propOutFile = open(propertiesFilename, 'w')
                subprocess.Popen(shlex.split("adb shell getprop"),stdout=propOutFile)
                print '        DEVICE PROPERTIES WRITTEN TO '+propertiesFilename+'.  PLEASE POST ON FAILURE.'

            if not ('Type' in option):
                # Skip to start of initial condition
                skipLines(file, 'Initial Conditions', option)

                # Build the list of initial conditions and display
                buildList(file, initialCondList, 'Procedure')
                print '\n\nInitial Conditions:'
                for line in initialCondList: print line,

                # Build the list of procedural steps and requirements then display them interleaved
                if buildList(file, procedureList, 'Definition and applicability'):
                    print '\n\nProcedure:'
                    processProcedureStep(test, procedureList, option)

                # Wait for acknowledgement from reader to move on to next test if not running through check
                if not('check' in option):
                    raw_input('\n        PRESS RETURN TO PROCEEED TO NEXT TEST OR CTRL C TO ABORT SUITE')
                    returnCode = True
                else:
                    print '\n\n'
            if not('check' in option or 'nolog' in option):
                logcatOutFile.close()
                propOutFile.close()
        else:
            raw_input(test+' from test list was NOT found in the procedure!')
    return(returnCode)


# MAIN
# Check arguments and handle appropriately
if len(sys.argv) <= 1:
    print (sys.version_info,' on ',sys.platform)
    print('\n\n\n\nUsage:')
    print(sys.argv[0]+' Procedure TestList Option\n')
    print('Procedure = The procedure file name extracted from Google Docs as a text file')
    print('TestList = The test list file name consisting of one test number per line (e.g. 4.4.32)')
    print('Options:')
    print(availOptions.keys())
    for opt in availOptions:
        print('  '+opt+': '+availOptions[opt])
elif len(sys.argv) >= 2:
    if len(sys.argv) >= 3: # Use list of tests file
        testList = open(sys.argv[2],'r').read().splitlines()
        numberOfTestsToRun = len(testList)
        if len(sys.argv) == 4:
            option = sys.argv[3]
            if not(option in availOptions.keys()):
                print 'Invalid option:'+sys.argv[3]+' Valid options:'
                for opt in availOptions:
                    print('  '+opt)
                exit()
        else:
            option=''
        if 'titles' in option:
            for title in testList:
                procFile=open(sys.argv[1], 'r')
                found = False
                line = ' '
                while not(line == ''):
                    line = procFile.readline()
                    if not(found):
                        found=title in line
                if not(found):
                    print('*******['+title+"] not found in procedure file")
                procFile.close()
        else:
            if not('check' in option or 'purpose' in option):
                waitForUSBConnection()
            for test in testList:
                if not(test==''):    # Guard against blank lines (usually at end of test list file)
                    # Force initial state
                    if not('check' in option):
                        print 'Setting DUT to initial state'
                        adbShellCommand('svc','data','enable') #enable cell data
                        adbShellCommand('svc','wifi','enable') #enable WiFi
                        adbShellCommand('dumpsys','deviceidle','step') #disable Doze mode

                    # open file each time as cases may not be in sequence
                    procFile=open(sys.argv[1], 'r')
                    parseByTest(procFile, test, option)
                    procFile.close()
    else: print('PLEASE INCLUDE BOTH PROCEDURE AND TEST FILES')
