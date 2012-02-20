#!/usr/bin/perl

use strict;
use bignum;
use Chart::Lines;

my $offset = 1 << 32;

my $db_dir = "/var/lib/trafcount";

my %FORM;

&parse_form;

if (($FORM{'host'}) && ($FORM{'date'}) && ($FORM{'graph'})) {
    &show_graph;
} elsif (($FORM{'host'}) && ($FORM{'date'})) {
    &print_stats;
} elsif ($FORM{'host'}) {
    &print_date;
} else {
    &print_host;
}

exit;

sub bytes_split()
{
    my $size = shift;
    my $return;

    my $kb = 1024;
    my $mb = 1024 * $kb;
    my $gb = 1024 * $mb;
    my $tb = 1024 * $gb;

    if ($size < $kb) {
        $return = sprintf("%s", $size);
    } elsif ($size < $mb) {
        $return = sprintf ("%.2f%s", $size / $kb, 'K');
    } elsif ($size < $gb) {
        $return = sprintf ("%.2f%s", $size / $mb, 'M');
    } elsif ($size < $tb) {
        $return = sprintf ("%.2f%s", $size / $gb, 'G');
    } else {
        $return = sprintf ("%.2f%s", $size / $tb, 'T');
    }

    return $return;
}

sub print_header()
{
    print <<_end_;
Content-type: text/html\n\n
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html><head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<link href="sarg.css" rel="stylesheet" type="text/css">
</head><body style="font-family: Tahoma,Verdana,Arial; font-size: 11px; background-color: rgb(255, 255, 255); background-image: url();">
<center><table cellpadding="0" cellspacing="0">
</tbody></table>
&nbsp;&nbsp;
<table cellpadding="0" cellspacing="0">
<tbody>
<tr>
<th class="title">Просмотр статистики счётчиков трафика</th></tr>
</tbody></table></center>
&nbsp;
<center><table cellpadding="1" cellspacing="2">
_end_
}

sub print_end()
{
    print "</tr></table></center>\n</body></html>\n";
}

sub print_host()
{
    my @host;
    my $i = 0;

    opendir(DBDIR, $db_dir);
    foreach my $file (readdir(DBDIR))
    {
	next if ($file !~ m/^(.*)\.db$/);
	$host[$i++] = $1;
    }
    closedir(DBDIR);

    &print_header;

    print '<tr><th class="header" align="center">No</th>';
    print '<th class="header" align="center">Host</th></tr>';

    $i = 1;
    foreach my $host (sort @host)
    {
	print "<tr><td class=\"data2\" align=\"right\">$i</td>\n";
	print "<td class=\"data2\" align=\"left\"><font color=\"blue\"><a href=\"?host=$host\">$host</a></font></td></tr>\n";
	$i++;
    }

    &print_end;
}

sub print_date()
{
    my $record;
    my %bytes_in;
    my %bytes_out;

    &print_header;

    print '<tr><th class="header" align="center">No</th>';
    print '<th class="header" align="center">&nbsp;</th>';
    print '<th class="header" align="center">Date</th>';
    print '<th class="header" align="center">Hostname</th>';
    print '<th class="header" align="center">In Bytes</th>';
    print '<th class="header" align="center">Out Bytes</th></tr>';

    open(DB, "$db_dir/$FORM{'host'}.db");

    do {
	read(DB, $record, 36);
        my ($date, undef, undef, undef, undef, $in_a, $in_b, $out_a, $out_b) = unpack("IL8", $record);

	if ($date) {
	    $date =~ s/^(\d{4})(\d{2})\d{2}$/$1$2/;

	    $bytes_in{$date} += $in_b * $offset + $in_a;
	    $bytes_out{$date} += $out_b * $offset + $out_a;
	}
    } while (!eof(DB));

    close(DB);

    my $i = 1;

    foreach my $date (reverse sort keys %bytes_in) {
	$date =~ m/^(\d{4})(\d{2})$/;

	print "<tr><td class=\"data2\" align=\"right\">$i</td>\n";
	print "<td class=\"data2\" align=\"right\"><a href=\"?host=$FORM{'host'}&date=$date&graph=1\"><img src=\"graph.png\" border=\"0\"></a></td>\n";
	print "<td class=\"data2\" align=\"right\"><font color=\"blue\"><a href=\"?host=$FORM{'host'}&date=$date\">$2.$1</a></font></td>\n";
	print "<td class=\"data2\" align=\"left\">$FORM{'host'}</td>\n";
	print "<td class=\"data2\" align=\"left\">" . &bytes_split($bytes_in{$date}) . "</td>\n";
	print "<td class=\"data2\" align=\"left\">" . &bytes_split($bytes_out{$date}) . "</td>\n";
	$i++;
    }

    &print_end;
}

sub print_stats()
{
    my $i = 0;
    my %bytes_in;
    my %bytes_out;

    &print_header;

    print '<tr><th class="header" align="center">No</th>';
    print '<th class="header" align="center">Date</th>';
    print '<th class="header" align="center">Hostname</th>';
    print '<th class="header" align="center">In Bytes</th>';
    print '<th class="header" align="center">Out Bytes</th></tr>';

    open(DB, "$db_dir/$FORM{'host'}.db");

    do {
	my $record;
	read(DB, $record, 36);
	my ($date, undef, undef, undef, undef, $in_a, $in_b, $out_a, $out_b) = unpack("IL8", $record);

	if ($date) {
	    $date =~ m/^(\d{4})(\d{2})\d{2}$/;
	    if ($FORM{'date'} eq "$1$2") {
		$bytes_in{$date} = $in_b * $offset + $in_a;
		$bytes_out{$date} = $out_b * $offset + $out_a;
	    }
	}
    } while (!eof(DB));

    close(DB);

    foreach my $record (reverse sort keys %bytes_in) {
        $record =~ m/^(\d{4})(\d{2})(\d{2})$/;
	$i++;

	print "<tr><td class=\"data2\" align=\"right\">$i</td>\n";
	print "<td class=\"data2\" align=\"left\">$3.$2.$1</td>\n";
	print "<td class=\"data2\" align=\"left\">$FORM{'host'}</td>\n";
	print "<td class=\"data2\" align=\"left\">" . &bytes_split($bytes_in{$record}) . "</td>\n";
	print "<td class=\"data2\" align=\"left\">" . &bytes_split($bytes_out{$record}) . "</td></tr>\n";
    }

    &print_end;
}

sub parse_form {
    my $buffer;

    # Get the input
    if ($ENV{'REQUEST_METHOD'} eq "POST") { read(STDIN, $buffer, $ENV{'CONTENT_LENGTH'}); }
    if ($ENV{'REQUEST_METHOD'} eq "GET") { $buffer = $ENV{'QUERY_STRING'}; }

    # Split the name-value pairs
    my @pairs = split(/&/, $buffer);

    foreach my $pair (@pairs) {
	my ($name, $value) = split(/=/, $pair);

        # Un-Webify plus signs and %-encoding
        $value =~ tr/+/ /;
        $value =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;

        $FORM{$name} = $value;
    }
}

sub show_graph {
    my %bytes_in;
    my %bytes_out;
    my @labels;
    my @input;
    my @output;

    open(DB, "$db_dir/$FORM{'host'}.db");

    do {
	my $record;
	read(DB, $record, 36);
	my ($date, undef, undef, undef, undef, $in_a, $in_b, $out_a, $out_b) = unpack("IL8", $record);

	if ($date) {
	    $date =~ m/^(\d{4})(\d{2})\d{2}$/;
	    if ($FORM{'date'} eq "$1$2") {
		$bytes_in{$date} = $in_b * $offset + $in_a;
		$bytes_out{$date} = $out_b * $offset + $out_a;
	    }
	}
    } while (!eof(DB));

    close(DB);

    my $i = 0;
    foreach my $date (sort keys %bytes_in) {
	$date =~ m/^\d{4}\d{2}(\d{2})$/;
	$labels[$i] = $1;
	$input[$i]  = $bytes_in{$date}/1024/1024;
	$output[$i] = $bytes_out{$date}/1024/1024;
	$i++;
    }

    my $obj = Chart::Lines->new(850, 350);

    my @data = (\@labels, \@input, \@output);

    $obj->set (
	'title'			=> "$FORM{'host'}",
	'sub_title'		=> $FORM{'date'},
	'x_label'		=> "Days",
	'y_label'		=> 'Megabytes',
	'legend_labels'		=> ['Input','Output'],
	'brush_size'		=> 4,
	'grid_lines'		=> 'true',
	'grey_background'	=> 'false',
	'colors'		=> {
		'background'	=> [255,255,255],
		'grid_lines'	=> [230,230,230],
		'dataset0'	=> [255,0,0],
		'dataset1'	=> [0,0,255]
	}
    );

    $obj->cgi_png(\@data);
}
