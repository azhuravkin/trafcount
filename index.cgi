#!/usr/bin/perl

use strict;
use Time::Local;
use POSIX "strftime";
use bignum;
use Switch;
use Chart::Lines;

my %ifname = (
    ppp0 => 'Internet',
);

my $offset = 1 << 32;

my $db_dir = "/var/lib/trafcount";

my %FORM;
my @years_list;

&parse_form;

switch ($FORM{'page'})
{
    case '6' { &page6; }
    case '5' { &page5; }
    case '4' { &page4; }
    case '3' { &page3; }
    case '2' { &page2; }
    case '1' { &page1; }
    else     { &page0; }
}

exit;

sub fill_years_list
{
    if ($FORM{'from_year'} < $FORM{'to_year'}) {
	for (my $year = $FORM{'from_year'}; $year <= $FORM{'to_year'}; $year++) {
	    push (@years_list, $year);
	}
    } elsif ($FORM{'from_year'} == $FORM{'to_year'}) {
	if (($FORM{'from_month'} > $FORM{'to_month'}) ||
		($FORM{'from_month'} == $FORM{'to_month'} &&
		$FORM{'from_day'} > $FORM{'to_day'})) {
	    return 1;
	}
	push (@years_list, $FORM{'from_year'});
    } else {
	return 1;
    }

    return 0;
}

sub page0
{
    my @years;
    my @now = localtime(time);

    my $Year = strftime("%Y", @now);
    my $Month = strftime("%m", @now);
    my $Day = strftime("%d", @now);

    opendir(DBDIR, $db_dir);
    foreach my $year (readdir(DBDIR))
    {
	next if (!(-d "$db_dir/$year") || ($year =~ m/^\./));
	push (@years, $year);
    }
    closedir(DBDIR);

    &print_header;

    if ($#years == -1) {
	print "<font color='red'>Нет данных</font>\n";
	&print_tail;
	exit;
    }

    print "<form><tr><th class='header3'>Укажите диапазон</th></tr>";
    print "<tr><td class='data'>с <select name='from_day'>\n";

    for (my $i = 1; $i <= 31; $i++) {
	printf("\t<option%s>%02d</option>\n", ($i == 1) ? " selected" : "", $i);
    }

    print "</select>.<select name='from_month'>\n";

    for (my $i = 1; $i <= 12; $i++) {
	printf("\t<option%s>%02d</option>\n", ($i == $Month) ? " selected" : "", $i);
    }

    print "</select>.<select name='from_year'>\n";

    for (my $i = 0; $i <= $#years; $i++) {
	printf("\t<option%s>%s</option>\n", ($years[$i] == $Year) ? " selected" : "", $years[$i]);
    }

    print "</select> по <select name='to_day'>\n";

    for (my $i = 1; $i <= 31; $i++) {
	printf("\t<option%s>%02d</option>\n", ($i == $Day) ? " selected" : "", $i);
    }

    print "</select>.<select name='to_month'>\n";

    for (my $i = 1; $i <= 12; $i++) {
	printf("\t<option%s>%02d</option>\n", ($i == $Month) ? " selected" : "", $i);
    }

    print "</select>.<select name='to_year'>\n";

    for (my $i = 0; $i <= $#years; $i++) {
	printf("\t<option%s>%s</option>\n", ($years[$i] == $Year) ? " selected" : "", $years[$i]);
    }

    print "</select>\n<input type='hidden' name='page' value='1'>\n";
    print "<input type='submit' value='Показать'></form></td></tr>";

    &print_tail;
}

sub page1
{
    my %hosts;

    &print_header;

    if (&fill_years_list) {
	print "<font color='red'>Дата указана не верно!</font>\n";
	&print_tail;
	return;
    }

    for (my $i = 0; $i <= $#years_list; $i++) {
	opendir(YEAR_DIR, "$db_dir/$years_list[$i]");
	foreach my $host (readdir(YEAR_DIR))
	{
	    next unless ((-d "$db_dir/$years_list[$i]/$host") && ($host !~ m/^\./));
	    &summ_on_hosts(\@{$hosts{$host}}, $years_list[$i], $host);
	}
	closedir(YEAR_DIR);
    }

    print "<tr><th class='header' align='center'>No</th>";
    print "<th class='header' align='center'>Host</th>";
    print "<th class='header' align='center'>Input</th>";
    print "<th class='header' align='center'>Output</th>";
    print "<th class='header' align='center'>&nbsp;</th></tr>";

    my $i = 1;
    foreach my $host (sort keys %hosts) {
	print "<tr><td class='data'>$i</td>";
	print "<td class='data2'><a href=\"?from_day=$FORM{'from_day'}&from_month=$FORM{'from_month'}&from_year=$FORM{'from_year'}";
	print "&to_day=$FORM{'to_day'}&to_month=$FORM{'to_month'}&to_year=$FORM{'to_year'}&page=2&host=$host\">$host</a></td>\n";
	print "<td class='data2'>" . &bytes_split($hosts{$host}[0]) . "</td>";
	print "<td class='data2'>" . &bytes_split($hosts{$host}[1]) . "</td>";

	print "<td class='data2'>\n<a href=\"?from_day=$FORM{'from_day'}&from_month=$FORM{'from_month'}&from_year=$FORM{'from_year'}&";
	print "to_day=$FORM{'to_day'}&to_month=$FORM{'to_month'}&to_year=$FORM{'to_year'}&page=3&host=$host\"><img src='datetime.png' border='0'></a>\n";

	print "<a href=\"?from_day=$FORM{'from_day'}&from_month=$FORM{'from_month'}&from_year=$FORM{'from_year'}&";
	print "to_day=$FORM{'to_day'}&to_month=$FORM{'to_month'}&to_year=$FORM{'to_year'}&page=4&host=$host\"><img src='graph.png' border='0'></a>\n</td></tr>";
	$i++;
    }

    &print_tail;
}

sub page2
{
    my %ifaces;

    &print_header;
    &fill_years_list;

    for (my $i = 0; $i <= $#years_list; $i++) {
	opendir(HOST_DIR, "$db_dir/$years_list[$i]/$FORM{'host'}");
	foreach my $iface (readdir(HOST_DIR))
	{
	    next if ($iface !~ m/^(.*)\.db$/);
	    &summ_on_ifaces(\@{$ifaces{$1}}, $years_list[$i], $1);
	}
	closedir(YEAR_DIR);
    }

    print "<tr><th class='header' align='center'>No</th>";
    print "<th class='header' align='center'>Interface</th>";
    print "<th class='header' align='center'>Input</th>";
    print "<th class='header' align='center'>Output</th>";
    print "<th class='header' align='center'>&nbsp;</th></tr>";

    my $i = 1;
    foreach my $iface (sort keys %ifaces) {
	print "<tr><td class='data'>$i</td>";
	printf "<td class='data2'>%s</td>\n", ($ifname{$iface}) ? $ifname{$iface} : $iface;
	print "<td class='data2'>" . &bytes_split($ifaces{$iface}[0]) . "</td>";
	print "<td class='data2'>" . &bytes_split($ifaces{$iface}[1]) . "</td>";
	print "<td class='data2'>\n<a href=\"?from_day=$FORM{'from_day'}&from_month=$FORM{'from_month'}&from_year=$FORM{'from_year'}";
	print "&to_day=$FORM{'to_day'}&to_month=$FORM{'to_month'}&to_year=$FORM{'to_year'}&page=5&host=$FORM{'host'}&iface=$iface\"><img src='datetime.png' border='0'></a>\n";
	print "<a href=\"?from_day=$FORM{'from_day'}&from_month=$FORM{'from_month'}&from_year=$FORM{'from_year'}";
	print "&to_day=$FORM{'to_day'}&to_month=$FORM{'to_month'}&to_year=$FORM{'to_year'}&page=6&host=$FORM{'host'}&iface=$iface\"><img src='graph.png' border='0'></a>\n</td></tr>\n";
	$i++;
    }

    &print_tail;
}

sub page3 {
    my %bytes_in;
    my %bytes_out;

    &print_header;
    &fill_years_list;

    for (my $i = 0; $i <= $#years_list; $i++) {
	opendir(HOST_DIR, "$db_dir/$years_list[$i]/$FORM{'host'}");
	foreach my $iface (readdir(HOST_DIR))
	{
	    next if ($iface !~ m/^(.*)\.db$/);
	    open(DB, "$db_dir/$years_list[$i]/$FORM{'host'}/$iface");

	    do {
		my $record;
		read(DB, $record, 36);
		my ($date, undef, undef, undef, undef, $in_a, $in_b, $out_a, $out_b) = unpack("IL8", $record);

		if ($date >= $FORM{'from_year'} . $FORM{'from_month'} . $FORM{'from_day'} &&
			$date <= $FORM{'to_year'} . $FORM{'to_month'} . $FORM{'to_day'}) {
		    $bytes_in{$date} += $in_b * $offset + $in_a;
		    $bytes_out{$date} += $out_b * $offset + $out_a;
		}
	    } while (!eof(DB));
	}
	close(DB);
    }
    closedir(YEAR_DIR);

    print "<table><tr><th class='header' align='center'>No</th>\n";
    print "<th class='header' align='center'>Date</th>\n";
    print "<th class='header' align='center'>Input</th>\n";
    print "<th class='header' align='center'>Output</th></tr>\n";

    my $i = 1;
    foreach my $date (sort keys %bytes_in) {
        $date =~ m/^(\d{4})(\d{2})(\d{2})$/;
	print "<tr><td class='data'>$i</td>\n";
	print "<td class='data2'>$3.$2.$1</td>\n";
	print "<td class='data2'>" . &bytes_split($bytes_in{$date}) . "</td>\n";
	print "<td class='data2'>" . &bytes_split($bytes_out{$date}) . "</td>\n</tr>";
	$i++;
    }

    &print_tail;
}

sub page4 {
    my %bytes_in;
    my %bytes_out;
    my @labels;
    my @input;
    my @output;

    &fill_years_list;

    for (my $i = 0; $i <= $#years_list; $i++) {
	opendir(HOST_DIR, "$db_dir/$years_list[$i]/$FORM{'host'}");
	foreach my $iface (readdir(HOST_DIR))
	{
	    next if ($iface !~ m/^(.*)\.db$/);
	    open(DB, "$db_dir/$years_list[$i]/$FORM{'host'}/$iface");

	    do {
		my $record;
		read(DB, $record, 36);
		my ($date, undef, undef, undef, undef, $in_a, $in_b, $out_a, $out_b) = unpack("IL8", $record);

		if ($date >= $FORM{'from_year'} . $FORM{'from_month'} . $FORM{'from_day'} &&
			$date <= $FORM{'to_year'} . $FORM{'to_month'} . $FORM{'to_day'}) {
		    $bytes_in{$date} += $in_b * $offset + $in_a;
		    $bytes_out{$date} += $out_b * $offset + $out_a;
		}
	    } while (!eof(DB));
	}
	close(DB);
    }
    closedir(YEAR_DIR);

    foreach my $date (sort keys %bytes_in) {
	$date =~ m/^(\d{4})(\d{2})(\d{2})$/;
	push (@labels, "$3.$2.$1");
	push (@input, $bytes_in{$date}/1024/1024);
	push (@output, $bytes_out{$date}/1024/1024);
    }

    my $obj = Chart::Lines->new(850, 350);
    my @data = (\@labels, \@input, \@output);

    $obj->set (
	'title'			=> "$FORM{'host'}",
	'sub_title'		=> $FORM{'date'},
	'x_label'		=> "Days",
	'y_label'		=> 'Megabytes',
	'x_ticks'		=> 'vertical',
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

sub page5 {
    my %bytes_in;
    my %bytes_out;

    &print_header;
    &fill_years_list;

    for (my $i = 0; $i <= $#years_list; $i++) {
	open(DB, "$db_dir/$years_list[$i]/$FORM{'host'}/$FORM{'iface'}.db");

	do {
	    my $record;
	    read(DB, $record, 36);
	    my ($date, undef, undef, undef, undef, $in_a, $in_b, $out_a, $out_b) = unpack("IL8", $record);

	    if ($date >= $FORM{'from_year'} . $FORM{'from_month'} . $FORM{'from_day'} &&
		    $date <= $FORM{'to_year'} . $FORM{'to_month'} . $FORM{'to_day'}) {
		$bytes_in{$date} += $in_b * $offset + $in_a;
		$bytes_out{$date} += $out_b * $offset + $out_a;
	    }
	} while (!eof(DB));

	close(DB);
    }

    print "<table><tr><th class='header' align='center'>No</th>\n";
    print "<th class='header' align='center'>Date</th>\n";
    print "<th class='header' align='center'>Input</th>\n";
    print "<th class='header' align='center'>Output</th></tr>\n";

    my $i = 1;
    foreach my $date (sort keys %bytes_in) {
        $date =~ m/^(\d{4})(\d{2})(\d{2})$/;
	print "<tr><td class='data'>$i</td>\n";
	print "<td class='data2'>$3.$2.$1</td>\n";
	print "<td class='data2'>" . &bytes_split($bytes_in{$date}) . "</td>\n";
	print "<td class='data2'>" . &bytes_split($bytes_out{$date}) . "</td>\n</tr>";
	$i++;
    }

    &print_tail;
}

sub page6 {
    my %bytes_in;
    my %bytes_out;
    my @labels;
    my @input;
    my @output;

    &fill_years_list;

    for (my $i = 0; $i <= $#years_list; $i++) {
	open(DB, "$db_dir/$years_list[$i]/$FORM{'host'}/$FORM{'iface'}.db");

	do {
	    my $record;
	    read(DB, $record, 36);
	    my ($date, undef, undef, undef, undef, $in_a, $in_b, $out_a, $out_b) = unpack("IL8", $record);

	    if ($date >= $FORM{'from_year'} . $FORM{'from_month'} . $FORM{'from_day'} &&
		    $date <= $FORM{'to_year'} . $FORM{'to_month'} . $FORM{'to_day'}) {
		$bytes_in{$date} += $in_b * $offset + $in_a;
		$bytes_out{$date} += $out_b * $offset + $out_a;
	    }
	} while (!eof(DB));

	close(DB);
    }

    foreach my $date (sort keys %bytes_in) {
	$date =~ m/^(\d{4})(\d{2})(\d{2})$/;
	push (@labels, "$3.$2.$1");
	push (@input, $bytes_in{$date}/1024/1024);
	push (@output, $bytes_out{$date}/1024/1024);
    }

    my $obj = Chart::Lines->new(850, 350);
    my @data = (\@labels, \@input, \@output);

    my $title = sprintf("%s (%s)", $FORM{'host'}, ($ifname{$FORM{'iface'}}) ? $ifname{$FORM{'iface'}} : $FORM{'iface'});

    $obj->set (
	'title'			=> $title,
	'sub_title'		=> $FORM{'date'},
	'x_label'		=> "Days",
	'y_label'		=> 'Megabytes',
	'x_ticks'		=> 'vertical',
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

sub summ_on_hosts
{
    my $ref = shift;
    my $year = shift;
    my $host = shift;

    opendir(DBDIR, "$db_dir/$year/$host");

    foreach my $iface (readdir(DBDIR))
    {
	next if ($iface !~ m/\.db$/);

	open(DB, "$db_dir/$year/$host/$iface");

	do {
	    my $record;
	    read(DB, $record, 36);
	    my ($date, undef, undef, undef, undef, $in_a, $in_b, $out_a, $out_b) = unpack("IL8", $record);

	    if ($date >= $FORM{'from_year'} . $FORM{'from_month'} . $FORM{'from_day'} &&
		$date <= $FORM{'to_year'} . $FORM{'to_month'} . $FORM{'to_day'}) {

		$$ref[0] += $in_b * $offset + $in_a;
		$$ref[1] += $out_b * $offset + $out_a;
	    }
	} while (!eof(DB));

        close(DB);
    }

    closedir(DBDIR);
}

sub summ_on_ifaces
{
    my $ref = shift;
    my $year = shift;
    my $iface = shift;

    opendir(DBDIR, "$db_dir/$year/$FORM{'host'}");

    open(DB, "$db_dir/$year/$FORM{'host'}/$iface.db");

    do {
	my $record;
	read(DB, $record, 36);
	my ($date, undef, undef, undef, undef, $in_a, $in_b, $out_a, $out_b) = unpack("IL8", $record);

	if ($date >= $FORM{'from_year'} . $FORM{'from_month'} . $FORM{'from_day'} &&
	    $date <= $FORM{'to_year'} . $FORM{'to_month'} . $FORM{'to_day'}) {

	    $$ref[0] += $in_b * $offset + $in_a;
	    $$ref[1] += $out_b * $offset + $out_a;
	}
    } while (!eof(DB));

    close(DB);
}

sub bytes_split()
{
    my $size = shift;
    my $return;

    my $kb = 1024;
    my $mb = 1024 * $kb;
    my $gb = 1024 * $mb;
    my $tb = 1024 * $gb;

    if ($size < $kb) {
        $return = sprintf("%d", $size);
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

sub print_header
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

sub print_tail
{
    print "</tr></table></center>\n</body></html>\n";
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
