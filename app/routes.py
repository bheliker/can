from flask import render_template, redirect, url_for, request
from app import app
import datetime, json

sizelimit = 1000

import os
basedir = os.path.abspath(os.path.dirname(__file__))

@app.route('/')
def index():
	return render_template('index.html')
	return "Hello, World, again!"

@app.route('/result', methods=['GET', 'POST'])
def translate_can():
	format = int(request.form.get('format'))
	try:
		year = int(request.form.get('year'))
		month = int(request.form.get('month'))
		day = int(request.form.get('day'))
	except:
		month = 1
		day = 1
		year = 1970
		
	
	try:
		testime = datetime.datetime(year,month,day)
	except:
		return "Invalid Date"
	
	if format == 0:
		try:
			output = parseString(request.form.get('candata'))
		except:
			return ("Error 4: Unparsable")

		try:
			translatedData, unknown = parseCL2k(output, year, month, day)
			csv = toCSV(translatedData)
		except Exception as E:
			return "Error 3: Unparsable: "+ str(E)
			
	elif format == 1: 
		try:
			output = parseCANDumpString(request.form.get('candata'))
		except Exception as E:
			return "Error 2: Unparsable: "+ str(E)

		try:
			translatedData, unknown = parseCANdumpdata(output)
			csv = toCSV(translatedData)
		except Exception as E:
			return "Error 2: Unparsable: "+ str(E)
	else:
		return ('Please Select Format')
	
	if len(translatedData)==0 and len(unknown)==0:
		return ("Error 0: No parsable data. Check your format")
	
	#return (csv)
	return render_template('results.html', translatedData=translatedData, csv=csv, unknown=str(unknown)).encode( "utf-8" )





@app.route('/can1')
def can2():
	rawdata_filepath = './0000002a.TXT'
	month = 7
	day = 31
	year = 1970
	rawdata = parseFile(rawdata_filepath)
	translatedData = parseCL2k(rawdata, year, month, day)
	return str(translatedData)

def toCSV(candataarray):
	csv = "Sig,PGN,Value,Units,Time\n"
	for each in candataarray:
		for point in each:
			csv += (str(point) + ",")
		csv = csv[:-1]+"\n"
	return csv

def parseString(string_data):
	CANdata=[] #parsed payload
	for each in string_data.split('\n'):
		if len(CANdata) > sizelimit:
			break
		try:
			data = each.translate({ord(c): None for c in ' \r\n'}).split(';') #splits into four parts: time, bus, PGN, data `04T124059196;1;18eeff0b;c009c40600090200`
			if len(data) == 4:
				if len(data[3]) < 7:
					data[3] = data[3].zfill(8) # fill the DATA with 0s if it isn't a full 8 bytes. Could fill with FFs I guess.
				CANdata.append(data)
		except:
			CANdata.append('Parsing Error'+str(each))
	return CANdata


def parseCANDumpString(string_data):
	CANdata=[] #parsed payload
	for each in string_data.split('\n'):
		if len(CANdata) > sizelimit:
			break
		try:
			data = each.translate({ord(c): None for c in ')(\r\n'})
			data = data.split(' ')
			if len(data) > 1:
				data[0] = data[0].translate({ord(c): None for c in '()'})
				data.append(data[2].split('#')[1])
				data[2] = data[2].split('#')[0]
				if len(data) == 4:
					if len(data[3]) < 7:
						data[3] = data[3].zfill(8) # fill the DATA with 0s if it isn't a full 8 bytes. Could fill with FFs I guess.
					CANdata.append(data)
		except:
			CANdata.append('Parsing Error'+str(each)+'\n')
	return CANdata



def parseFile(rawdata_filepath):
	CANdata=[] #parsed payload
	with open(rawdata_filepath) as f:
		for line in f: # parse the file line by line into PGN and SPNpayload arrays. There's a less ram heavy way to do this I'm sure
			data = line.translate([None, ' \n']).split(';') #splits into four parts: time, bus, PGN, data `04T124059196;1;18eeff0b;c009c40600090200`
			if len(data[3]) < 7:
				data[3] = data[3].zfill(8) # fill the DATA with 0s if it isn't a full 8 bytes. Could fill with FFs I guess.
			CANdata.append(data)
	return CANdata

def parseSPNposition(rawSPN): #this field is written to be human readable and is annoying. Why don't they just specify a start and length? Why the range??
	if '.' in rawSPN: #SPNs using BITS DON'T WORK
		length = 0
		start = float(rawSPN[0:1])
		bytes = False
	elif '-' in rawSPN: #parse the byte range
		try:
			length = int(rawSPN[-1]) - int(rawSPN[0])+1
			start = int(rawSPN[0])
			bytes = True
		except: #catch weird things
			length = 0
			start = 0
			bytes = False
	elif '*' in rawSPN: #catch things like "Variable - up to 200 bytes followed by an "*" delimiter"
		length = 0
		start = 0
		bytes = False
	else:
		if len(rawSPN) == 1:
			start = int(rawSPN)
			length = 1
			bytes = True
		else: #be really lazy and just throw everything away that doesn't easily parse. Come back to it later. 
			start = 0
			length = 0
			bytes = False
	return int(start), length, bytes #return start byte and length (bits return length of 0 right now)

def parseCL2k(rawdata, year, month, day):
	PGN_definitions_file = os.path.join(basedir, 'SPNs_and_PGNs2_noDesc.json')
	PGN_file = open(PGN_definitions_file, 'r')
	PGN_json=json.load(PGN_file)	
	
	missingPGNs = []
	unparsedSPNs = []
	arrayofSPNs = []
	translatedData = []
	
	for frame in rawdata:
		if len(translatedData) > sizelimit:
			break
		ID=frame[2] #PGN
		PStext=ID[-4:-2] # PDU specific. Either destination address or group extension. AKA DA. 
		PFtext=ID[-6:-4] # PF: PDU format: < 240, PS is destination address. (PDU1 format); >= 240, PS is group extension. (PDU2 format)
		PGNtext=PFtext+PStext
	
		PGNint2=int(PGNtext,16)
	
		PGNdata = frame[3] # The Data
		if (len(PGNdata) != 16):
			continue #just drop data packages that aren't 16 bytes, they're probably errors.
 
		byteArray = [0, PGNdata[0:2], PGNdata[2:4], PGNdata[4:6], PGNdata[6:8], PGNdata[8:10], PGNdata[10:12], PGNdata[12:14], PGNdata[14:16]]
		epochtime = parseTimetoEpochms(year,month,day,frame[0])
 
		if str(PGNint2) in PGN_json:
			if len(PGN_json[str(PGNint2)]) == 31: #account for PGNs with only 1 SPN, then for everything else:
				PGNstructure = [PGN_json[str(PGNint2)]]
			else:
				PGNstructure = []
				for i in range(0,len(PGN_json[str(PGNint2)])-1):
					PGNstructure.append(PGN_json[str(PGNint2)][i]) 
 
			for suspects in range(0,len(PGNstructure)):
				PGNname, SPNname, SPNlength, SPNstart, multiplier, offset, bytes = parseSPNs(PGN_json[str(PGNint2)][suspects])			  
				if bytes == True:
					value = determineSPNValue(SPNlength, SPNstart, multiplier, offset, byteArray)
				elif bytes == False:
					value = getValueforBits(PGN_json[str(PGNint2)][suspects], byteArray)				
				else: 
					value = "Can't Parse"
					unparsedSPNs.append([SPNname.encode('utf8')+' - '+str(PGN_json[str(PGNint2)][suspects]['SPN']), PGN_json[str(PGNint2)][suspects]['SPN']])
				
				if value != 'ERR':# and SPNname.encode('utf8') == "Engine Speed":
					translatedData.append([SPNname.encode('utf8'), PGN_json[str(PGNint2)][suspects]['SPN'], value, PGN_json[str(PGNint2)][suspects]['Units'].encode('utf8'), epochtime])
					arrayofSPNs.append([SPNname.encode('utf8'),PGN_json[str(PGNint2)][suspects]['SPN']])
		else:
			missingPGNs.append(PGNint2)
	return translatedData, missingPGNs

def parseCANdumpdata(rawdata):
	PGN_definitions_file = os.path.join(basedir, 'SPNs_and_PGNs2_noDesc.json')
	PGN_file = open(PGN_definitions_file, 'r')
	PGN_json=json.load(PGN_file)	
	
	missingPGNs = []
	unparsedSPNs = []
	arrayofSPNs = []
	translatedData = []

	for frame in rawdata:
		if len(translatedData) > sizelimit:
			break
		ID=frame[2] #PGN
		PStext=ID[-4:-2] # PDU specific. Either destination address or group extension. AKA DA. 
		PFtext=ID[-6:-4] # PF: PDU format: < 240, PS is destination address. (PDU1 format); >= 240, PS is group extension. (PDU2 format)
		PGNtext=PFtext+PStext
		PGNint2=int(PGNtext,16)
	
		PGNdata = frame[3] # The Data
		if (len(PGNdata) != 16):
			continue #just drop data packages that aren't 16 bytes, they're probably errors.
 
		byteArray = [0, PGNdata[0:2], PGNdata[2:4], PGNdata[4:6], PGNdata[6:8], PGNdata[8:10], PGNdata[10:12], PGNdata[12:14], PGNdata[14:16]]
		
		epochtime = (frame[0])
 
		if str(PGNint2) in PGN_json:
			if len(PGN_json[str(PGNint2)]) == 31: #account for PGNs with only 1 SPN, then for everything else:
				PGNstructure = [PGN_json[str(PGNint2)]]
			else:
				PGNstructure = []
				for i in range(0,len(PGN_json[str(PGNint2)])-1):
					PGNstructure.append(PGN_json[str(PGNint2)][i]) 
 
			for suspects in range(0,len(PGNstructure)):
				PGNname, SPNname, SPNlength, SPNstart, multiplier, offset, bytes = parseSPNs(PGN_json[str(PGNint2)][suspects])			  
				if bytes == True:
					value = determineSPNValue(SPNlength, SPNstart, multiplier, offset, byteArray)
				elif bytes == False:
					value = getValueforBits(PGN_json[str(PGNint2)][suspects], byteArray)				
				else: 
					value = "Can't Parse"
					unparsedSPNs.append([SPNname.encode('utf8')+' - '+str(PGN_json[str(PGNint2)][suspects]['SPN']), PGN_json[str(PGNint2)][suspects]['SPN']])
				
				if value != 'ERR':# and SPNname.encode('utf8') == "Engine Speed":
					translatedData.append([SPNname.encode('utf8'), PGN_json[str(PGNint2)][suspects]['SPN'], value, PGN_json[str(PGNint2)][suspects]['Units'].encode('utf8'), epochtime])
					arrayofSPNs.append([SPNname.encode('utf8'),PGN_json[str(PGNint2)][suspects]['SPN']])
		else:
			missingPGNs.append(PGNint2)


	return translatedData, missingPGNs



def createMultiplierfromResolution(resolutionHumanReadable):
	from simpleeval import simple_eval
	resolutionArray = resolutionHumanReadable.split(' ') #should return stuff like `1/8192`
	try:
		multiplier = simple_eval(resolutionArray[0]) # dangerous but it works because we control the source JSON. 
	except:
		multiplier = 1
		#print "Error in multiplier:", resolutionHumanReadable
	return multiplier

def getOffset(offsetHR):
	intermediate = offsetHR.split(' ')
	try:
		offset = float(intermediate[0])
	except:
		offset = 0
		#print "Offset error:", offsetHR
	return offset

def determineSPNValue(SPNlength, SPNstart, multiplier, offset, byteArray):
	finalBytes = ''
	emptyBytes = 0
	
	if SPNstart == 0:
		SPNstart = 1 # I think if SPN start is 0 we have an error anyway? I can't remember. 
		
	for count in range (SPNstart,SPNstart+SPNlength): #the bytes are added together in reverse order. 
		try:
			if byteArray[count] == 'FF':
				emptyBytes += 1
			finalBytes = byteArray[count] + finalBytes
		except: 
			print( 'error in determineSPNValue', byteArray, SPNstart, SPNlength, count)
			continue
	try:
		value = int(finalBytes,16) * multiplier + offset
	except:
		value = "Empty Value"
	
	if emptyBytes == SPNlength: #this just means every byte is `FF` - I don't care about that data
		value = "ERR" #easy to filter on
	#print byteArray, finalBytes, value
	
	return value

def parseSPNs(PGNpayload):
	PGNname = PGNpayload['Parameter Group Label']
	SPNname = PGNpayload['SPN Name'].replace(',', '')
	
	try:
		SPNlength = int(PGNpayload['SPN Length'][0]) #length of SPN in bits or bytes
	except:
		print( "Error in parseSPNs:",PGNpayload['SPN Length'])
		SPNlength = 0
		
	SPNstart, SPNlength2, bytes = parseSPNposition(PGNpayload['SPN Position in PGN'])
#	  if SPNlength != SPNlength2: # error checking? Do we need it? this fails because I'm ignoring bits so I'm commenting out for now.
#		  print "error with SPNlength", SPNlength, SPNlength2, bytes

	try:
		multiplier = createMultiplierfromResolution(PGNpayload['Resolution'])
	except:
		multiplier = 1
	
	try:
		offset = getOffset(PGNpayload['Offset'])
	except:
		offset = 0
		
	#rewrite this since I'm barely using the parseSPNposition anymore?
	if 'byte' in PGNpayload['SPN Length']:
		bytes = True
	elif 'bit' in PGNpayload['SPN Length']:
		bytes = False 
	else:
		#print( "error in parseSPNs:", PGNpayload['SPN Length'])
		bytes = False
		
	return PGNname, SPNname, SPNlength, SPNstart, multiplier, offset, bytes

def getValueforBits(PGNpayload, byteArray):
	if 'bit' in PGNpayload['SPN Length']:
		try:
			startbit = float(PGNpayload['SPN Position in PGN'])
			sizebits = int(PGNpayload['SPN Length'][0])
			bytes = False
		except:
			#print( "ERR:",PGNpayload['SPN Position in PGN'], PGNpayload['SPN Length'][0])
			startbit = 0
			sizebits = 0
			bytes = True
	else:
		bytes = True
		value = 0
		
	if bytes == False:
		binaryRepofByte = bin(int(byteArray[int(startbit)], base=16)).lstrip('0b')
		start = int(str(startbit).split('.')[-1])
		end = sizebits + start
		value = binaryRepofByte[start:end]
		try:
			value = int(value,2)
		except:
			value = 0
	else:
		value = 'ERR'
	return value

def parseTimetoEpochms(y,m,d,canlogger2000time):
	canlogger2000time = canlogger2000time.split('T')
	d = int(canlogger2000time[0])
	theTime = datetime.datetime(y,m,d,int(canlogger2000time[1][0:2]),int(canlogger2000time[1][2:4]),int(canlogger2000time[1][4:6]),int(canlogger2000time[1][6:])*1000)
	epochtime = (theTime - datetime.datetime(1970,1,1)).total_seconds()*1000
	return int(epochtime)

