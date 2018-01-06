#!/usr/bin/python
#filter_licences.py v 2.0
#Copyright John Sincock, 2017
#
#Pls forgive the pretty low-quality code.
#This is my first real go at doing anything in python. In the past, I've always used perl for this sort of thing.
#
# Script to filter the Tenements_Live.kml listing from WA Dept of Mines, Industry, Regulation and Safety:
# https://dasc.dmp.wa.gov.au/dasc/ -> Statewide spatial datasets -> Tenements -> Current (live and pending)
# Direct link is currently:
# https://dasc.dmp.wa.gov.au/DASC/Download/File/5
#
# The dataset zipfile contains several .kmz files, ie Tenements_Live.kmz and Tenements_Pending.kmz
# Unzip the Tenements_Live.kmz so it becomes Tenements_Live.kml, and then you can use this script to filter it for particular lease or license types.
#
# Uses:
# 1) Filter for particular licence types, like EXPLORATION LICENCE, (note: add delimiters > and < eg if you want to exclude EXPLORATION LICENCE OFFSHORE").
# 2) Can also be used to find tenements belonging to a particular person, if you know the full name they are registering under, eg: 
#        SURNAME, FIRSTNAME MIDDLENAME
# 3) Can exclude tenements outside a bounding box specified in a file:
#        cat bounds/bounds-kalgoorlie.csv 
#        #Kalgoorlie Area:
#        #topleft
#        #bottomright
#        -27.80, 119.90
#        -32.34, 124.05
# 4) Can exclude based on Tenement start date and end date.
#
# Todo:
#   1)

from __future__ import print_function
import sys
import re
import time
import collections

CONST_NOT_IN_FILTER=-1                                  #values >=0 represent the index of the filter that matched.

def initialise_switches ():
    old_date=time.strptime("01/01/1901", "%d/%m/%Y")
    new_date=time.strptime("1/1/3000", "%d/%m/%Y")
    switches={'use_stdin':1,                            #are we reading input from file (false) or stdin (true) #expect kml input file via stdin by default
              'path_to_file':"",                        #path to input file, if we're not using stdin
              'pattern_file':"",                        #path to pattern file.
              'use_filter':0,                           #whether to restrict to tenements within specified filter
              'use_dates':{'use_start_date_lower':0, 'use_start_date_upper':0, 'use_end_date_lower':0, 'use_end_date_upper':0},
              'filtering_dead':0,                       #0, when filtering live tenements, 1 when filtering dead tenements, which have different formats for some fields.
              'use_bounds':0,                           #whether to restrict to tenements within specified bounding box
              'bounds_file':"./bounds/bounds.csv",      #bounding box:
              'add_pins':0,                             #add a pin at upper left corner of each tenement.
              'pin_style_file':"./pins/pin-styles.kml", #file containing the pin-styles used by google earth.
              'pin_prefix':[],                          #pins are named according to optional pin prefix on each line of pattern file, with tenement id appended
              'dates': {'start_date_lower':old_date, 'start_date_upper': new_date, 'end_date_lower': old_date, 'end_date_upper': new_date}
    }
    return switches
    
def warn (message):
    print (message, file=sys.stderr)
    #print (message, file=sys.stderr, flush=true)
    return

def usage ():
    warn ("")
    warn ("usage> ./filter_licences.py [ -p ] [ -f InputFile ] [ -b \"bounds_file\" ] [ -F \"filter_patterns_file\" ] [ \"Filter Pattern\" ] > OutputFile")
    warn ("Eg:")
    warn ("usage> ./filter_licences.py -f Tenements_Live.kml \">EXPLORATION LICENCE<\" > Tenements_Live_Exploration.kml")
    warn ("usage> cat Tenements_Live.kml | ./filter_licences.pl -p -F \"filter_patterns.pat\" > Tenements_Live_Exploration.kml")
    warn ("")
    warn ("Options:")
    warn ("  -b  bounds_file             Read boundary of included area from file. (Format below)")
    warn ("  -d                          Adjust scan for different format of dead tenements file.")
    warn ("  -h                          Display help")
    warn ("  -p                          Creates a yellow pin at upper left of each tenement (makes it easier to see small tenements in Google Earth).")
    warn ("                              Optional pin prefix can be specified at start of each line in pattern file #delimited by#. Pin names = tenement id appended to this prefix.")
    warn ("  -e  dd/mm/yyyy              Only keep records with End Date >= date.")
    warn ("  -E  dd/mm/yyyy              Only keep records with End Date <= date.")
    warn ("  -s  dd/mm/yyyy              Only keep records with Start Date >= date.")
    warn ("  -S  dd/mm/yyyy              Only keep records with Start Date <= date.")
    warn ("  -F  filter_patterns_file    Specify file with one or more search strings. (Format below).")
    warn ("")
    warn ("Tenement types:")
    warn ("                \"EXPLORATION LICENCE\"")
    warn ("                \"EXPLORATION LICENCE OFFSHORE\"")
    warn ("                \"CHRISTMAS ISLAND EXPLORATION LICENCE\"")
    warn ("                \"PROSPECTING LICENCE\"")
    warn ("                \"RETENTION LICENCE\"")
    warn ("                \"MISCELLANEOUS LICENCE\"")
    warn ("                \"LICENCE TO TREAT TAILINGS\"")
    warn ("                \"MINING LEASE\"")
    warn ("                \"COAL MINING LEASE\"")
    warn ("                \"MINERAL LEASE\"")
    warn ("                \"MINERAL LEASE S.A.\"")
    warn ("                \"GENERAL PURPOSE LEASE\"")
    warn ("                \"GENERAL PURPOSE LEASE S.A.\"")
    warn ("                \"TEMPORARY RESERVE\"")
    warn ("                And possibly others.")
    warn ("")
    warn ("Bounding box file format (lat/long coords in decimal degrees:")
    warn ("  topleft_latitude, topleft_longitude")
    warn ("  bottomright_latitude, bottomright_longitude")
    warn ("")
    warn ("Patterns file format:")
    warn ("  #optional_pin_prefix#Some string to search for")
    warn ("  Another string to search for")
    warn ("  #another pin prefix delimited by hash symbols#Yet another search string")
    warn ("")            
    return

def read_pattern_file (pattern_file):
#build filter_array, array of tenement types, or other strings to filter for
    filter_array=[]     #tenement type or other pattern to filter for.
    filter_lines=[]     #lines of the pattern file
    pin_prefix=[]       #prefix for pins matching each filter
    warn ("Reading filter patterns from: " + pattern_file + ":")
    handle = open(pattern_file, 'r')
    filter_lines=handle.read().splitlines()
    handle.close()

    filter_index=0
    for line in filter_lines:
        #warn ("Looking for pin name in line: " + line)
        m=re.search('^#([^#]*)#(.*)',line)
        if m:
            pin_prefix.append(m.group(1)) 
            #warn ("Pin prefix[" + str(filter_index) + "]=" + pin_prefix[filter_index])
            filter_array.append(m.group(2))
        else:
            filter_array.append(line)
            pin_prefix.append("") 
        filter_index+=1
    
    warn ("Filter_array=")
    warn (filter_array)
    warn ("Reading patterns done.")
    return (filter_array, pin_prefix)

def parse_args ():
    filter_array=[]
    num_of_params = len(sys.argv)
    switches=initialise_switches()
    bounds=collections.namedtuple('Bounds', ['min_long', 'max_long', 'min_lat', 'max_lat'])
    #warn ("num_of_params=" + str(num_of_params))
    if num_of_params == 1:
        usage()
        exit(1)
    switches['use_stdin']=1   #expect kml input file via stdin by default
    i=1
    while i < num_of_params :
        #warn ("i=" + str(i))
        if sys.argv[i] == "-h": 
            usage()
            exit(1)
        if sys.argv[i] == "-F": 
            i+=1
            switches['pattern_file']=sys.argv[i]
            warn ("Using pattern_file: " + switches['pattern_file'])
            (filter_array, switches['pin_prefix'])=read_pattern_file(switches['pattern_file'])
            switches['use_filter']=1
        elif sys.argv[i] == "-f":
            i+=1 
            switches['use_stdin']=0
            switches['path_to_file']=sys.argv[i]
            warn ("path_to_file: " + switches['path_to_file'])
        elif sys.argv[i] == "-b":
            i+=1 
            switches['use_bounds']=1
            switches['bounds_file']=sys.argv[i]
            warn ("bounds_file: " + switches['bounds_file'])           
            bounds=read_bounds_file(switches['bounds_file'])
        elif sys.argv[i] == "-p":
            switches['add_pins']=1
            warn ("Will add pins.")
        elif sys.argv[i] == "-s":
            i+=1 
            switches['use_dates']['use_start_date_lower']=1
            date=sys.argv[i]
            warn ("Filtering by start date >= " + date)
            switches['dates']['start_date_lower']=time.strptime(date, "%d/%m/%Y")
        elif sys.argv[i] == "-S":
            i+=1
            switches['use_dates']['use_start_date_upper']=1
            date=sys.argv[i]
            warn ("Filtering by start date <= " + date)
            switches['dates']['start_date_upper']=time.strptime(date, "%d/%m/%Y")
        elif sys.argv[i] == "-e":
            i+=1
            switches['use_dates']['use_end_date_lower']=1
            date=sys.argv[i]
            warn ("Filtering by end date >=" + date)
            switches['dates']['end_date_lower']=time.strptime(date, "%d/%m/%Y")
        elif sys.argv[i] == "-E":
            i+=1 
            switches['use_dates']['use_end_date_upper']=1
            date=sys.argv[i]
            warn ("Filtering by end date <=" + date)
            switches['dates']['end_date_upper']=time.strptime(date, "%d/%m/%Y")
        elif sys.argv[i] == "-d":
            switches['filtering_dead']=1
            warn ("Filtering dead tenements.")
        else:
            filter_array.append(sys.argv[i])
            warn ("filter_array: ")
            warn (filter_array)
            switches['use_filter']=1    
        i+=1
    return (filter_array, bounds, switches)

def read_file (path_to_file,use_stdin):
    if use_stdin == 0:
       warn ("Reading path_to_file: "+ path_to_file)
       handle=open(path_to_file, 'r')
    else:
       warn ("Reading STDIN:")
       handle=sys.stdin

    lines = handle.read().splitlines()
    handle.close()
    warn ("Reading input done.")
    #warn (lines)
    return lines

def read_bounds_file (bounds_file):
    warn ("Reading bounds_file: "+ bounds_file)
    handle=open(bounds_file, 'r')
    bounds_data=handle.read().splitlines()
    handle.close()

    bounds=collections.namedtuple('Bounds', ['min_long', 'max_long', 'min_lat', 'max_lat'])
    topleft=0
    for line in bounds_data:
        if "#" in line:
            #warn ("  Skipping comment: " + line)
            continue
        else:
            if topleft==0:
                #warn ("  Parsing topleft: " + line)
                coord = line.replace(' ','').split(',')
                bounds.max_lat=coord[0]
                bounds.min_long=coord[1]
                topleft=1
                warn ( "  max_lat,min_long=" + str(bounds.max_lat) + "," + str(bounds.min_long) )
            else:
                #warn ("  Parsing bottomright: " + line)
                coord = line.replace(' ','').split(',')
                bounds.min_lat=coord[0]
                bounds.max_long=coord[1]
                warn ( "  min_lat,max_long=" + str(bounds.min_lat) + "," + str(bounds.max_long) )
                break
    #warn ("Reading bounds done.")
    return bounds

def dump_lines (lines):
    warn ("No of lines=" + str(len(lines)) )
    warn ("Read lines:")
    #print (lines)
    return

def dump_record (record_index, indexes, lines):
    #warn ("    Dumping record number " + str( (record_index+1) ) )
    record_slice=lines[ indexes['record_line_indexes'][record_index] : indexes['record_end_line_indexes'][record_index]+1 ]
    for line in record_slice:
       print(line)
    return

def dump_header (regexp_marker, lines):
#dump from first line until we reach a line like: <Placemark id="blah">
    warn ("Dumping header.")
    for line in lines:
        if re.search(regexp_marker,line):
           break #break out of loop      
        else:
           print(line)
    return

def dump_pin_styles (pin_style_file):
    warn ("Reading pin styles from: " + pin_style_file)
    handle=open(pin_style_file, 'r')
    pin_styles = handle.read().splitlines()
    #warn ("Reading pin styles done.\n")
    for line in pin_styles:
       print(line)
    handle.close()
    return

def dump_pin (PIN_NAME, DESCRIPTION, LONGITUDE, LATITUDE):
    print ("<Placemark>")
    print ("  <name>" + PIN_NAME + "</name>")
    print ("    <description>" + DESCRIPTION)
    print ("    </description>")
    print ("    <styleUrl>#m_ylw-pushpin</styleUrl>")
    print ("    <Point>")
    print ("       <gx:drawOrder>1</gx:drawOrder>")
    print ("       <coordinates>" + LONGITUDE + "," + LATITUDE + ",0</coordinates>")
    print ("    </Point>")
    print ("</Placemark>")
    return


#Each record is like:
#<Placemark id="kml_9">
#<name>CML 12/448</name>
#<snippet> </snippet>
#<description><![CDATA[<center><table><tr><th colspan='2' align='center'><em>Att#ributes</em></th></tr><tr bgcolor="#E3E3F3">
#<th>Tenement ID</th>
#<td>CML1200448</td>
#</tr><tr bgcolor="">
#<th>Tenement Type</th>
#<td>COAL MINING LEASE</td>
#...
#</Placemark>

def get_pin_fields (pin_prefix, record, record_index, indexes):
    j=0
    while j < len(record):
       line=record[j]
       #warn ("    Parsing: " + line)
       if "<name>" in line:   
           m=re.search('.*?<name>([^<>]+)<\/name>.*',line)
           filter_index=indexes['record_in_filter'][record_index]
           PIN_NAME = pin_prefix[filter_index] + m.group(1)
           #PIN_NAME = pin_prefix + m.group(1)
           DESCRIPTION=m.group(1)
           warn ("      Pin name = " + PIN_NAME)

       #tenement coords are listed thus, in each record:
       #<coordinates>121.816666674544,-30.6500000038417,0 121.816666674544,-30.6666666590608,0 121.816666674544,-30.6833333303453,0 ...
       #We'll use just the first Longitude & Latitude, which is upper left corner.

       if  "<coordinates>" in line:
           #warn ("      Extracting pin coords from line=" + line)
           m=re.search('^<coordinates>\s*([^,]+),([^,]+),.*',line)    #this is the slow one on several records which have coords lines which have many many coords
           LONGITUDE = m.group(1)
           LATITUDE = m.group(2)
           #warn ("    Pin Longitude=" + LONGITUDE)
           #warn ("    Pin Latitude=" + LATITUDE)
           break  #some tenements seem to have two sets of coords... for now we just create a pin at upper left of first set, and ignore any other coord sets.
       j+=1
    #warn ("      Pin fields obtained.")
    return (PIN_NAME,DESCRIPTION,LONGITUDE,LATITUDE)

def get_coords (record):
    j=0
    while j < len(record):
       line=record[j]
       #warn ("    Parsing: " + line)

       #tenement coords are listed thus, in each record:
       #<coordinates>121.816666674544,-30.6500000038417,0 121.816666674544,-30.6666666590608,0 121.816666674544,-30.6833333303453,0 ...
       #We'll use just the first Longitude & Latitude, which is upper left corner.

       if  "<coordinates>" in line:
           #warn ("      Extracting coords from line=" + line)
           m=re.search('^<coordinates>\s*([^,]+),([^,]+),.*',line)    #this is the slow one on several records which have coords lines which have many many coords
           LONGITUDE = m.group(1)
           LATITUDE = m.group(2)
           #warn ("    Longitude=" + LONGITUDE)
           #warn ("    Latitude=" + LATITUDE)
           break  #some tenements seem to have two sets of coords... for now we just create a pin at upper left of first set, and ignore any other coord sets.
       j+=1
    #warn ("      Lat/Long obtained.")
    return (LONGITUDE,LATITUDE)

def find_records (start_marker, end_marker, lines):
    warn ("Finding tenement records:")
    warn ("No of lines=" + str(len(lines)) )
    record_line_indexes=[]                  #line numbers for start of each tenement record.
    record_end_line_indexes=[]              #line numbers for end of each tenement record.
    record_in_filter=[]                     #whether each record was matched by filter & position restrictions
    line_index=0
    no_of_records=0

    for line in lines:
        if start_marker in line:
            record_line_indexes.append(line_index)
            #warn ("Record " + str( (no_of_records+1) ) + " starts at line " + str( (line_index+1) ) )
            record_in_filter.append(0)  #just append something so there is a value there
        elif end_marker in line:
            record_end_line_indexes.append(line_index)
            #warn ("Record " + str( (no_of_records+1) ) + " ends at line " + str( (line_index+1) ) )
            no_of_records+=1
            #warn ("No of records=" + str(no_of_records) )
        #else:
        #    warn ("Can't see " + start_marker + " or " + end_marker + " in " + line)
        line_index+=1
    warn ("  Total tenements : " + str(no_of_records))
    indexes={'record_line_indexes': record_line_indexes, 'record_end_line_indexes': record_end_line_indexes, 'record_in_filter': record_in_filter}
    return (no_of_records, indexes)

def check_position (record, bounds):
    OK=1
    (longitude,latitude)=get_coords(record)
    #warn ("      longitude=" + longitude)
    if float(longitude) < float(bounds.min_long):
        #warn ("      Longitude too small: " + longitude + " < " + min_long)
        OK=0
    if float(longitude) > float(bounds.max_long):
        #warn ("      Longitude too big: " + longitude + " > " + max_long)
        OK=0
        
    #warn ("      latitude=" + latitude)
    if float(latitude) < float(bounds.min_lat):
        #warn ("      Latitude too small: " + latitude + " < " + min_lat)
        OK=0
    if float(latitude) > float(bounds.max_lat):
        #warn ("      Latitude too big: " + latitude + " > " + max_lat)
        OK=0
    return OK

def filter_records (filter_array, indexes, lines):
    record_index=0
    filter_matches=0  #number of records matching filter.
    warn ("Matching against filter_array:")
    print(filter_array, file=sys.stderr)
    for record_start in indexes['record_line_indexes']:
       #warn ("  Checking record " + str((record_index+1)) + " starting at line " + str((record_start+1)) + ", ending at line " + str((indexes['record_end_line_indexes'][record_index]+1)) )
       record_slice=lines[ record_start : indexes['record_end_line_indexes'][record_index]+1 ]
       matched=0
       indexes['record_in_filter'][record_index]=CONST_NOT_IN_FILTER
       for line in record_slice:
           #warn ("Matching line:" + line)
           filter_index=0
           for filter in filter_array:
               if filter in line:  #sufficient, and much faster than regexes
                  matched=1
       	          filter_matches+=1
                  indexes['record_in_filter'][record_index]=filter_index
       	          #warn ("    Record " + str((record_index+1)) + " matches filter index: " + str(filter_index) + " " + filter + ".")
       	          break
               filter_index+=1
           if matched==1:
       	       break #Tenement type is present twice in each record so only dump record and increment count on first occurrence.
       record_index+=1

    warn ("Tenements matching patterns : " + str(filter_matches) + ".")
    return (filter_matches, indexes['record_in_filter'])

def bound_records (bounds, indexes, lines):
    record_index=0
    position_matches=0
    warn ("Filtering via bounding box:")
    for record_start in indexes['record_line_indexes']:
       #warn ("  Checking record " + str((record_index+1)) + " starting at line " + str((record_start+1)) + ", ending at line " + str((record_end_line_indexes[record_index]+1)) )
       record_slice=lines[ record_start : indexes['record_end_line_indexes'][record_index]+1 ]
       if indexes['record_in_filter'][record_index]!=CONST_NOT_IN_FILTER:
           #for line in record_slice:
            position_matched=check_position(record_slice, bounds)
            if position_matched==1:
                position_matches+=1
            else:
                indexes['record_in_filter'][record_index]=CONST_NOT_IN_FILTER
       record_index+=1
    warn ("Tenements matching patterns and position : " + str(position_matches) + ".")
    return indexes['record_in_filter']

def get_date (line,marker,dateformat):
    #<SimpleData name="Start Date">12/08/2017</SimpleData>
    thisdate=re.search('^.*?\>(.*)\<.*?',line)  #yay
    if thisdate:
        date_obj=time.strptime(thisdate.group(1), dateformat)
    else:
        date_obj=time.strptime("1/1/0001", "%d/%m/%Y")
        warn ("Could not get date from line: " + line)
    return date_obj

def check_record_date (record_slice, mydate, marker, date_operator, dateformat):
    date_ok=0
    for line in record_slice:
        if marker in line:
            #warn ("Matching line: " + line)
            record_date=get_date(line,marker,dateformat)
            if date_operator==">=":
                if record_date >= mydate:
                    date_ok=1
            elif date_operator=="<=":
                if record_date <= mydate:
                    date_ok=1
    #if date_ok==1:
    #    warn ("Matched tenement with " + marker + " " + time.strftime(dateformat,record_date) + " " + date_operator + " " + time.strftime(dateformat,mydate))
    #else:
    #    warn ("No match for tenement with " + marker + " " + time.strftime(dateformat,record_date) + " " + date_operator + " " + time.strftime(dateformat,mydate))
    return date_ok

def check_date (mydate, marker, date_operator, dateformat, indexes, lines):
    record_index=0
    date_matches=0
    #warn ("Filtering via date:")
    #warn("Indexes[record_line_indexes] has: " + str(len(indexes['record_line_indexes'])) + " elements.")
    #warn("Indexes[record_end_line_indexes] has: " + str(len(indexes['record_end_line_indexes'])) + " elements.")
    for record_start in indexes['record_line_indexes']:
        record_slice=lines[ record_start : indexes['record_end_line_indexes'][record_index]+1 ]
        #warn ("Checking record: " + str(record_index) + " record_in_filter=" + str(indexes['record_in_filter'][record_index])  )
        if indexes['record_in_filter'][record_index]!=CONST_NOT_IN_FILTER:
            #warn ("Checking record: " + str(record_index))
            date_ok=check_record_date(record_slice, mydate, marker, date_operator, dateformat)
            if date_ok==1:
                date_matches+=1
            else:
                indexes['record_in_filter'][record_index]=CONST_NOT_IN_FILTER
        #else:
        #    warn("Record " + str(record_index) + " has already been excluded, it is not in the filtered set")
        record_index+=1
    warn ("Matching tenements with " + marker + " " + date_operator + " " + time.strftime(dateformat,mydate) + " = " + str(date_matches) + ".")
    return #indexes['record_in_filter']

def dump_records (add_pins, pin_prefix, no_of_records, indexes, lines):
    record_index=0
    warn ("Dumping all matching records:")
    for record_start in indexes['record_line_indexes']:
       record_slice=lines[ record_start : indexes['record_end_line_indexes'][record_index]+1 ]
       if indexes['record_in_filter'][record_index]!=CONST_NOT_IN_FILTER:
               dump_record (record_index, indexes, lines)  #dump the whole tenement record.
               if add_pins==1:
                    #Create a pin at first (upper left) coordinate of tenement boundary:
       	           (PIN_NAME, DESCRIPTION, LONGITUDE, LATITUDE) = get_pin_fields (pin_prefix, record_slice, record_index, indexes)
       	           dump_pin (PIN_NAME, DESCRIPTION, LONGITUDE, LATITUDE)
       record_index+=1
    return

def count_matches (record_in_filter):
    record_count=0
    warn ("Counting all matching records:")
    for record in record_in_filter:
        if record != CONST_NOT_IN_FILTER:
            record_count+=1
    warn ("Counted: " + str(record_count) + " records that have matched.")
    return

def dump_footer (no_of_records, indexes, lines):
    footer_start=indexes['record_end_line_indexes'][no_of_records-1]+1
    last_line_index=len(lines)-1 #index of last line in @lines
    footer_slice=lines[ footer_start :  last_line_index+1 ]   #a[start:end] # items start through end-1, ie end is index of element NOT included in slice
    #footer_slice=lines[ footer_start: ] #also works
    for line in footer_slice:
       print (line)
    return

def filter_tenements (filter_array, markers, date_format, switches, bounds, lines):
    dump_header(markers['header_marker'], lines)
    dump_pin_styles(switches['pin_style_file'])
    (no_of_records, indexes)=find_records(markers['start_marker'], markers['end_marker'], lines) #no of records found in data file
    
    if switches['use_filter']==1:
        (filter_matches, indexes['record_in_filter'])=filter_records(filter_array, indexes, lines)
    if switches['use_bounds']==1:
        indexes['record_in_filter']=bound_records(bounds, indexes, lines)

    if switches['use_dates']['use_start_date_lower']==1:
        #indexes['record_in_filter']=
        check_date(switches['dates']['start_date_lower'], markers['start_date_marker'], ">=", date_format, indexes, lines)
    if switches['use_dates']['use_start_date_upper']==1:
        #indexes['record_in_filter']=
        check_date(switches['dates']['start_date_upper'], markers['start_date_marker'], "<=", date_format, indexes, lines)
        
    if switches['use_dates']['use_end_date_lower']==1:
        #indexes['record_in_filter']=
        check_date(switches['dates']['end_date_lower'], markers['end_date_marker'], ">=", date_format, indexes, lines)
    if switches['use_dates']['use_end_date_upper']==1:
        #indexes['record_in_filter']=
        check_date(switches['dates']['end_date_upper'], markers['end_date_marker'], "<=", date_format, indexes, lines)

    dump_records(switches['add_pins'], switches['pin_prefix'], no_of_records, indexes, lines)
    dump_footer(no_of_records, indexes, lines)
    return

def main ():
    (filter_array, bounds, switches)=parse_args()
    lines=read_file(switches['path_to_file'], switches['use_stdin'])   #holds all lines of file.
    #warn ("main() : No of lines=" + str(len(lines)) )

    #dump_lines()
    if switches['filtering_dead']==1:
        markers={'start_date_marker': "<STARTDATE>", 'end_date_marker': "<ENDDATE>", 'header_marker': '^.*<DeadTenements>.*', 'start_marker': "<DeadTenements", 'end_marker': "</DeadTenements"}
        date_format="%Y%m%d"
    else:
        markers={'start_date_marker': "\"Start Date\"", 'end_date_marker': "\"End Date\"", 'header_marker': '<Placemark.*', 'start_marker': "<Placemark", 'end_marker': "</Placemark"}
        date_format="%d/%m/%Y"

    filter_tenements(filter_array, markers, date_format, switches, bounds, lines)
    warn ("Done.\n")
    return

#########
main()
