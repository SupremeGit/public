#!/usr/bin/perl
#filter_licences.pl
#Copyright John Sincock, 2017
#
# Simple script to filter the Tenements_Live.kml listing from WA Dept of Mines, Industry, Regulation and Safety:
# https://dasc.dmp.wa.gov.au/dasc/ -> Statewide spatial datasets -> Tenements -> Current (live and pending)
# Direct link is currently:
# https://dasc.dmp.wa.gov.au/DASC/Download/File/5
#
# The dataset zipfile contains several .kmz files, ie Tenements_Live.kmz and Tenements_Pending.kmz
# Unzip the Tenements_Live.kmz so it becomes Tenements_Live.kml, and then you can use this script to filter it for particular lease or license types.

use strict;
use warnings;

my @lines;                    #holds all lines of file
my $filter_matches=0;         #number of records matching filter
my @record_line_indexes;      #line numbers for start of each tenement record 
my @record_end_line_indexes;  #line numbers for end of each tenement record
my $no_of_records=0;
my $use_stdin;                #are we reading input from file (false) or stdin (true).
my $path_to_file;             #path to input file, if we're not using stdin
my $filter;                   #tenement type to filter for.

sub usage {
    warn "\n";
    warn "usage> ./filter_licences.pl Tenements_Live.kml \"EXPLORATION LICENCE\" > Tenements_Live_Exploration.kml\n";
    warn "usage> cat Tenements_Live.kml | ./filter_licences.pl \"tenement type\" > Tenements_Live_Exploration.kml\n";
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
    exit 1;
}

my $num_of_params = @ARGV;
if ( $num_of_params == 0 ) { usage; }
if ( $num_of_params == 1 ) {
    #warn "Reading from stdin:\n";
    $use_stdin = 1 ;  #if only one arg is present, let's assume it's the tenement type to filter for.
    $filter=">$ARGV[0]<"; #use >,< delimiters so we get eg EXPLORATION_LICENCE & exclude EXPLORATION LICENCE OFFSHORE
}
if ( $num_of_params == 2 ) {
    #warn "Reading from file:\n";
    $use_stdin = 0;
    $path_to_file=$ARGV[0];
    $filter=">$ARGV[1]<"; #use >,< delimiters
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
sub find_records {
    my $line_index=0;
    $no_of_records=0;
    warn "Finding tenement records:\n";
    foreach my $line (@lines) {
	if ($line =~ m/.*<Placemark.*/) {
	    push @record_line_indexes, $line_index;
	    #warn "Record " . ($no_of_records+1) . " starts at line " . ($line_index+1) . ".\n";
	}
	if ($line =~ m/.*<\/Placemark.*/) {
	    push @record_end_line_indexes, $line_index;
	    #warn "Record " . ($no_of_records+1) . " ends at line " . ($line_index+1) . ".\n";
	    $no_of_records++;
	}
	$line_index++;
    }
    warn "Total tenements : $no_of_records.\n";
}

sub dump_desired_records {
    my $record_index=0;
    $filter_matches=0;
    foreach my $record_start (@record_line_indexes) {
	#warn "Checking record " . ($record_index+1) . " starting at line " . ($record_start+1) . ", ending at line " . ($record_end_line_indexes[$record_index]+1) . ".\n";

	my @record_slice=@lines[ $record_start .. $record_end_line_indexes[$record_index] ];
	foreach my $line (@record_slice) {
	    if ($line =~ m/.*$filter.*/) {
		#warn "Record " . ($record_index+1) . " matches filter $filter.\n";
		$filter_matches++;
		dump_record ($record_index);
		last; #Tenement type is present twice in each record so only dump record and increment count on first occurrence.
	    }
	}
	$record_index++;
    }
    warn "Tenements on $filter : $filter_matches.\n";
}

sub dump_footer {
    my $footer_start=$record_end_line_indexes[$no_of_records-1]+1;
    my $last_line_index=@lines-1; #index of last line in @lines
    my @footer_slice=@lines[ $footer_start ..  $last_line_index ];
    foreach my $line (@footer_slice) {
	print "$line\n";
    }
}

sub filter {
    dump_header;
    find_records;
    dump_desired_records;
    dump_footer;
}

read_file;
filter;
warn "Done.\n";
