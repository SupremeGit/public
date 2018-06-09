#!/usr/bin/perl
#filter_licences.pl v 3.0
#Copyright John Sincock, 2017
#
# Simple script to filter the Tenements_Live.kml listing from WA Dept of Mines, Industry, Regulation and Safety:
# https://dasc.dmp.wa.gov.au/dasc/ -> Statewide spatial datasets -> Tenements -> Current (live and pending)
# Direct link is currently:
# https://dasc.dmp.wa.gov.au/DASC/Download/File/5
#
# The dataset zipfile contains several .kmz files, ie Tenements_Live.kmz and Tenements_Pending.kmz
# Unzip the Tenements_Live.kmz so it becomes Tenements_Live.kml, and then you can use this script to filter it for particular lease or license types.
#
# When filtering for licences, like EXPLORATION LICENCE, you should add delimiters >,< to exclude EXPLORATION LICENCE OFFSHORE.
#
# Can also be used to find tenements belonging to a particular person, if you know the full name they are registerign under, eg: 
#  SURNAME, FIRSTNAME MIDDLENAME

use strict;
use warnings;
no warnings 'experimental::smartmatch';
use Data::Dumper;

my @lines;                                   #holds all lines of file.
my $filter_matches=0;                        #number of records matching filter.
my @record_line_indexes;                     #line numbers for start of each tenement record. 
my @record_end_line_indexes;                 #line numbers for end of each tenement record.
my $no_of_records=0;
my $use_stdin;                               #are we reading input from file (false) or stdin (true).
my $path_to_file;                            #path to input file, if we're not using stdin
my $pattern_file;                            #path to pattern file.
my @filter_array;                            #tenement type to filter for.
my $pin_style_file="./pins/pin-styles.kml";  #file containing the pin-styles used by google earth.
my $add_pins=0;                              #add a pin at upper left corner of each tenement.

sub usage {
    warn "\n";
    warn "usage> ./filter_licences.pl [ -p ] [ -f InputFile ] [ -F \"filter_patterns_file\" ] [ \"Filter Pattern\" ] > OutputFile\n";
    warn "Eg:\n";
    warn "usage> ./filter_licences.pl -f Tenements_Live.kml \">EXPLORATION LICENCE<\" > Tenements_Live_Exploration.kml\n";
    warn "usage> cat Tenements_Live.kml | ./filter_licences.pl -p -F \"filter_patterns.pat\" > Tenements_Live_Exploration.kml\n";
    warn "\n";
    warn "Options:\n";
    warn "  -p            Creates a yellow pin at upper left of tenement (makes it easier to see small tenements in Google Earth).\n";
    warn "\n";
    warn "Tenement types:\n";
    warn "                \"EXPLORATION LICENCE\"\n";
    warn "                \"EXPLORATION LICENCE OFFSHORE\"\n";
    warn "                \"CHRISTMAS ISLAND EXPLORATION LICENCE\"\n";
    warn "                \"PROSPECTING LICENCE\"\n";
    warn "                \"RETENTION LICENCE\"\n";
    warn "                \"MISCELLANEOUS LICENCE\"\n";
    warn "                \"LICENCE TO TREAT TAILINGS\"\n";
    warn "                \"MINING LEASE\"\n";
    warn "                \"COAL MINING LEASE\"\n";
    warn "                \"MINERAL LEASE\"\n";
    warn "                \"MINERAL LEASE S.A.\"\n";
    warn "                \"GENERAL PURPOSE LEASE\"\n";
    warn "                \"GENERAL PURPOSE LEASE S.A.\"\n";
    warn "                \"TEMPORARY RESERVE\"\n";
    warn "                And possibly others.\n";
    warn "\n";
}

sub read_pattern_file {
    my $handle;
    #warn "Reading filter patterns from: $pattern_file:\n";
    open $handle, '<', $pattern_file;
    chomp(@filter_array = <$handle>);
    close $handle;
    warn Data::Dumper->Dump([\@filter_array], [qw(filter_array)]);
    #warn "Reading patterns done.\n";
}

sub parse_args {
    my $num_of_params = @ARGV;
    if ( $num_of_params == 0 ) { usage; exit 1; }
    $use_stdin = 1 ;  #expect kml input file via stdin by default
    for ( my $i=0; $i < $num_of_params; $i++) {
	if ( $ARGV[0] eq "-F" ) { 
	    shift @ARGV; $i++; 
	    $pattern_file=$ARGV[0];
	    read_pattern_file;
	} elsif ( $ARGV[0] eq "-f" ) {
	    shift @ARGV; $i++; 
	    $use_stdin = 0;
	    $path_to_file=$ARGV[0];
	} elsif ( $ARGV[0] eq "-p" ) {
	    $add_pins=1;
	} else {
	    @filter_array="$ARGV[0]";
	}
	shift @ARGV;
    }
}

sub read_file {
    my $handle;
    if ( $use_stdin == 0 ) {
	warn "Reading $path_to_file:\n";
	open $handle, '<', $path_to_file;
    }
    else {
	warn "Reading STDIN:\n";
	$handle="STDIN";
    }
    chomp(@lines = <$handle>);
    close $handle;
    #warn "Reading input done.\n";
}

sub dump_to_file {
    foreach my $line (@lines) {
	print "$line\n";
    }
}

sub dump_record {
    my $record_index=shift;
    #warn "Dumping record number " . ($record_index+1) . "\n";
    my @record_slice=@lines[ $record_line_indexes[$record_index] .. $record_end_line_indexes[$record_index] ];
    foreach my $line (@record_slice) {
	print "$line\n";
    }
}

sub dump_header {
#dump from first line until we reach a line like: <Placemark id="blah">
    foreach my $line (@lines) {
	if ($line =~ m/<Placemark.*/) {
	    last; #break out of loop      
	}
	else {
	    print "$line\n";
	}
    }
}

sub dump_pin_styles {
    my $handle;
    my @pin_styles;
    #warn "Reading pin styles from: $pin_style_file:\n";
    open $handle, '<', $pin_style_file;
    chomp(@pin_styles = <$handle>);
    close $handle;
    #warn "Reading pin styles done.\n";
    foreach my $line (@pin_styles) {
	print "$line\n";
    }
}

sub dump_pin {
    my ($PIN_NAME, $DESCRIPTION, $LONGITUDE, $LATITUDE) = @_;
    print "<Placemark>\n";
    print "  <name>$PIN_NAME</name>\n";
    print "    <description>$DESCRIPTION\n";
    print "    </description>\n";
    print "    <styleUrl>#m_ylw-pushpin</styleUrl>\n";
    print "    <Point>\n";
    print "	<gx:drawOrder>1</gx:drawOrder>\n";
    print "	<coordinates>$LONGITUDE,$LATITUDE,0</coordinates>\n";
    print "    </Point>\n";
    print "</Placemark>\n";
}


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

sub get_pin_fields {
    my ($description, $PIN_NAME, $DESCRIPTION, $LONGITUDE, $LATITUDE, @record) = @_;
    my $line;
    my $j=0;
    while ( $j < @record ) {
	$line=$record[$j];
	#warn "    Parsing: $line\n";
	if ($line =~ m/.*<name>.*/) {
	    $line =~ m/.*<name>([^<>]+)<\/name>.*/ ;
	    $$PIN_NAME = $1 ;
	    warn "    Pin name = $$PIN_NAME\n";
	}
	#tenement coords are listed thus, in each record:
	#<coordinates>121.816666674544,-30.6500000038417,0 121.816666674544,-30.6666666590608,0 121.816666674544,-30.6833333303453,0 ...
	#We'll use just the first Longitude & Latitude, which is upper left corner.
	$line=$record[$j];
	if ($line =~ m/.*<coordinates>.*/) {
	    #warn "    Pin Coords=$line\n";
	    $line =~ m/<coordinates>\s*([^,]+),([^,]+),.*/;
	    $$LONGITUDE = $1;
	    $$LATITUDE = $2;
	    #warn "    Pin Longitude=$$LONGITUDE\n";
	    #warn "    Pin Latitude=$$LATITUDE\n";
	    last;  #some tenements seem to have two sets of coords... for now we just create a pin at upper left of first set, and ignore any other coord sets.
	}
	$j++;
    }
    $$DESCRIPTION="$description";
}

sub find_records {
    my $line_index=0;
    $no_of_records=0;
    warn "Finding tenement records:\n";
    foreach my $line (@lines) {
	if ($line =~ m/.*<Placemark.*/) {
	    push @record_line_indexes, $line_index;
	    warn "Record " . ($no_of_records+1) . " starts at line " . ($line_index+1) . ".\n";
	}
	if ($line =~ m/.*<\/Placemark.*/) {
	    push @record_end_line_indexes, $line_index;
	    warn "Record " . ($no_of_records+1) . " ends at line " . ($line_index+1) . ".\n";
	    $no_of_records++;
	}
	$line_index++;
    }
    warn "  Total tenements : $no_of_records.\n";
}

sub dump_desired_records {
    my $record_index=0;
    $filter_matches=0;
    warn "Looking for matches:\n";
    foreach my $record_start (@record_line_indexes) {
	#warn "  Checking record " . ($record_index+1) . " starting at line " . ($record_start+1) . ", ending at line " . ($record_end_line_indexes[$record_index]+1) . ".\n";

	my $matched;
	my $filter;
	my $description;
	my @record_slice=@lines[ $record_start .. $record_end_line_indexes[$record_index] ];
	foreach my $line (@record_slice) {
	    $matched=0;
	    #if ($line ~~ @filter_array ) { #smartmatch is useless, just doesn't seem to work on perl 5.24
	    foreach $filter (@filter_array) {
		#warn "Checking for match vs filter: $filter";
		#if ($line =~ m/.*>$filter<.*/) {
		if ($line =~ m/.*$filter.*/) {
		    $matched=1;
		    warn "  Record " . ($record_index+1) . " matches filter: $filter.\n";
		    $description=$filter;
		    last;
		}
	    }
	    if ($matched==1) {
		    $filter_matches++;
		    dump_record ($record_index);  #dump the whole tenement record.
		    if ($add_pins==1) {	    
			#Create a pin at first (upper left) coordinate of tenement boundary:
			my ($PIN_NAME, $DESCRIPTION, $LONGITUDE, $LATITUDE);
			get_pin_fields ($description, \$PIN_NAME, \$DESCRIPTION, \$LONGITUDE, \$LATITUDE, @record_slice);
			dump_pin ($PIN_NAME, $DESCRIPTION, $LONGITUDE, $LATITUDE);
		    }
		    last; #Tenement type is present twice in each record so only dump record and increment count on first occurrence.
	    }
	}
	$record_index++;
    }
    warn "Tenements matching patterns : $filter_matches.\n";
}

sub dump_footer {
    my $footer_start=$record_end_line_indexes[$no_of_records-1]+1;
    my $last_line_index=@lines-1; #index of last line in @lines

    #warn "last_line_index=$last_line_index\n";
    #warn "last_line= @lines[$last_line_index]\n";
    my @footer_slice=@lines[ $footer_start ..  $last_line_index ];
    foreach my $line (@footer_slice) {
	print "$line\n";
    }
}

sub dofilter {
    dump_header;
    dump_pin_styles;
    find_records;
    dump_desired_records;
    dump_footer;
}

parse_args;
read_file;
dofilter;
warn "Done.\n";
