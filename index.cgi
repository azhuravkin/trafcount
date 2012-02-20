#!/usr/bin/perl

use strict;
use Time::Local;
use POSIX "strftime";
use bignum;
use Switch;
use Socket;
use Chart::Lines;

my %alias = (
    ppp0 => 'Internet',
);

my $offset = 1 << 32;

my $db_dir = "/var/lib/trafcount";

my %FORM;
my @years_list;

&parse_form;

switch ($FORM{'page'}) {
    case '8' { &page8; }
    case '7' { &page7; }
    case '6' { &page6; }
    case '5' { &page5; }
    case '4' { &page4; }
    case '3' { &page3; }
    case '2' { &page2; }
    case '1' { &page1; }
    else     { &page0; }
}

exit;

sub resolve {
    return gethostbyaddr(inet_aton(shift), AF_INET);
}

sub fill_years_list {
    if ($FORM{'year1'} < $FORM{'year2'}) {
	for (my $year = $FORM{'year1'}; $year <= $FORM{'year2'}; $year++) {
	    push (@years_list, $year);
	}
    } elsif ($FORM{'year1'} == $FORM{'year2'}) {
	if (($FORM{'month1'} > $FORM{'month2'}) ||
		($FORM{'month1'} == $FORM{'month2'} &&
		$FORM{'day1'} > $FORM{'day2'})) {
	    return 1;
	}
	push (@years_list, $FORM{'year1'});
    } else {
	return 1;
    }

    return 0;
}

sub page0 {
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
    print "<tr><td class='data'>с <select name='day1'>\n";

    for (my $i = 1; $i <= 31; $i++) {
	printf("\t<option%s>%02d</option>\n", ($i == 1) ? " selected" : "", $i);
    }

    print "</select>.<select name='month1'>\n";

    for (my $i = 1; $i <= 12; $i++) {
	printf("\t<option%s>%02d</option>\n", ($i == $Month) ? " selected" : "", $i);
    }

    print "</select>.<select name='year1'>\n";

    for (my $i = 0; $i <= $#years; $i++) {
	printf("\t<option%s>%s</option>\n", ($years[$i] == $Year) ? " selected" : "", $years[$i]);
    }

    print "</select> по <select name='day2'>\n";

    for (my $i = 1; $i <= 31; $i++) {
	printf("\t<option%s>%02d</option>\n", ($i == $Day) ? " selected" : "", $i);
    }

    print "</select>.<select name='month2'>\n";

    for (my $i = 1; $i <= 12; $i++) {
	printf("\t<option%s>%02d</option>\n", ($i == $Month) ? " selected" : "", $i);
    }

    print "</select>.<select name='year2'>\n";

    for (my $i = 0; $i <= $#years; $i++) {
	printf("\t<option%s>%s</option>\n", ($years[$i] == $Year) ? " selected" : "", $years[$i]);
    }

    print "</select>\n<input type='hidden' name='page' value='1'>\n";
    print "<input type='submit' value='Показать'></form></td></tr>";

    &print_tail;
}

sub page1 {
    my %hosts;
    my %resolved;

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
	    next if ($host !~ m/^(.*)\.intf$/);
	    &summ(\%hosts, $years_list[$i], $host, $1);
	}
	closedir(YEAR_DIR);
    }

    print "<tr><th class='header' align='center'>No</th>";
    print "<th class='header' align='center'>Host</th>";
    print "<th class='header' align='center'>Input</th>";
    print "<th class='header' align='center'>Output</th>";
    print "<th class='header' align='center'>&nbsp;</th></tr>";

    foreach my $host (sort keys %hosts) {
	$resolved{&resolve($host)} = $host;
    }

    my $i;
    foreach my $host (sort keys %resolved) {
	printf "<tr><td class='data'>%d</td>", ++$i;
	print "<td class='data2'><a href=\"?day1=$FORM{'day1'}&month1=$FORM{'month1'}&year1=$FORM{'year1'}";
	print "&day2=$FORM{'day2'}&month2=$FORM{'month2'}&year2=$FORM{'year2'}&page=2&host=$resolved{$host}\">$host</a></td>\n";
	print "<td class='data2'>" . &bytes_split($hosts{$resolved{$host}}[0]) . "</td>";
	print "<td class='data2'>" . &bytes_split($hosts{$resolved{$host}}[1]) . "</td>";
	print "<td class='data2'>\n<a href=\"?day1=$FORM{'day1'}&month1=$FORM{'month1'}&year1=$FORM{'year1'}&";
	print "day2=$FORM{'day2'}&month2=$FORM{'month2'}&year2=$FORM{'year2'}&page=3&host=$resolved{$host}\"><img src='datetime.png' border='0'></a>\n";
	print "<a href=\"?day1=$FORM{'day1'}&month1=$FORM{'month1'}&year1=$FORM{'year1'}&";
	print "day2=$FORM{'day2'}&month2=$FORM{'month2'}&year2=$FORM{'year2'}&page=4&host=$resolved{$host}\"><img src='graph.png' border='0'></a>\n</td></tr>";
    }

    &print_tail;
}

sub page2 {
    my %ifaces;

    &print_header;
    &fill_years_list;

    for (my $i = 0; $i <= $#years_list; $i++) {
	&summ(\%ifaces, $years_list[$i], $FORM{'host'} . ".intf");
    }

    print "<tr><th class='header' align='center'>No</th>";
    print "<th class='header' align='center'>Interface</th>";
    print "<th class='header' align='center'>Input</th>";
    print "<th class='header' align='center'>Output</th>";
    print "<th class='header' align='center'>&nbsp;</th></tr>";

    my $i;
    foreach my $iface (sort keys %ifaces) {
	printf "<tr><td class='data'>%d</td>", ++$i;
	printf "<td class='data2'>%s</td>\n", ($alias{$iface}) ? $alias{$iface} : $iface;
	print "<td class='data2'>" . &bytes_split($ifaces{$iface}[0]) . "</td>";
	print "<td class='data2'>" . &bytes_split($ifaces{$iface}[1]) . "</td>";
	print "<td class='data2'>\n<a href=\"?day1=$FORM{'day1'}&month1=$FORM{'month1'}&year1=$FORM{'year1'}";
	print "&day2=$FORM{'day2'}&month2=$FORM{'month2'}&year2=$FORM{'year2'}&page=6&host=$FORM{'host'}&iface=$iface\"><img src='datetime.png' border='0'></a>\n";
	print "<a href=\"?day1=$FORM{'day1'}&month1=$FORM{'month1'}&year1=$FORM{'year1'}";
	print "&day2=$FORM{'day2'}&month2=$FORM{'month2'}&year2=$FORM{'year2'}&page=7&host=$FORM{'host'}&iface=$iface\"><img src='graph.png' border='0'></a>\n</td></tr>\n";
    }

    &print_tail;
}

sub page3 {
    my %dates;

    &print_header;
    &fill_years_list;

    for (my $i = 0; $i <= $#years_list; $i++) {
	opendir(YEAR_DIR, "$db_dir/$years_list[$i]");
	foreach my $host (readdir(YEAR_DIR))
	{
	    next if ($host !~ m/\.intf$/);
	    &summ(\%dates, $years_list[$i], $host);
	}
	closedir(YEAR_DIR);
    }

    print "<table><tr><th class='header' align='center'>No</th>\n";
    print "<th class='header' align='center'>Date</th>\n";
    print "<th class='header' align='center'>Input</th>\n";
    print "<th class='header' align='center'>Output</th></tr>\n";

    my $i;
    foreach my $date (sort keys %dates) {
        $date =~ m/^(\d{4})(\d{2})(\d{2})$/;
	printf "<tr><td class='data'>%d</td>\n", ++$i;
	print "<td class='data2'>$3.$2.$1</td>\n";
	print "<td class='data2'>" . &bytes_split($dates{$date}[0]) . "</td>\n";
	print "<td class='data2'>" . &bytes_split($dates{$date}[1]) . "</td>\n</tr>";
    }

    &print_tail;
}

sub page4 {
    my %dates;
    my @labels;
    my @input;
    my @output;

    &fill_years_list;

    for (my $i = 0; $i <= $#years_list; $i++) {
	opendir(YEAR_DIR, "$db_dir/$years_list[$i]");
	foreach my $host (readdir(YEAR_DIR))
	{
	    next if ($host !~ m/\.intf$/);
	    &summ(\%dates, $years_list[$i], $host);
	}
	closedir(YEAR_DIR);
    }

    foreach my $date (sort keys %dates) {
	$date =~ m/^(\d{4})(\d{2})(\d{2})$/;
	push (@labels, "$3.$2.$1");
	push (@input, $dates{$date}[0]/1024/1024);
	push (@output, $dates{$date}[1]/1024/1024);
    }

    my $obj = Chart::Lines->new(850, 350);
    my @data = (\@labels, \@input, \@output);

    $obj->set (
	'title'			=> &resolve($FORM{'host'}),
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
	    'dataset0'		=> [255,0,0],
	    'dataset1'		=> [0,0,255]
	}
    );

    $obj->cgi_png(\@data);
}

sub page5 {
    my %dates;
    my @labels;
    my @tmp;

    &fill_years_list;

    for (my $i = 0; $i <= $#years_list; $i++) {
	opendir(YEAR_DIR, "$db_dir/$years_list[$i]");
	foreach my $host (readdir(YEAR_DIR)) {
	    next if ($host !~ m/\.type$/);
	    &summ(\%dates, $years_list[$i], $host);
	}
	closedir(YEAR_DIR);
    }

    foreach my $date (sort keys %dates) {
	$date =~ m/^(\d{4})(\d{2})(\d{2})$/;
	push (@labels, "$3.$2.$1");
	for (my $i = 0; $i <= $#{$dates{$date}}; $i++) {
	    push (@{$tmp[$i]}, $dates{$date}[$i]/1024/1024);
	}
    }

    my $obj = Chart::Lines->new(850, 350);
    my @data = (\@labels, @tmp);

    $obj->set (
	'title'			=> "All Hosts",
	'sub_title'		=> $FORM{'date'},
	'x_label'		=> "Days",
	'y_label'		=> 'Megabytes',
	'x_ticks'		=> 'vertical',
	'legend_labels'		=> ['Other','Web', 'Mail'],
	'brush_size'		=> 4,
	'grid_lines'		=> 'true',
	'grey_background'	=> 'false',
	'colors'		=> {
	    'background'	=> [255,255,255],
	    'grid_lines'	=> [230,230,230]
	}
    );

    $obj->cgi_png(\@data);
}

sub page6 {
    my %dates;

    &print_header;
    &fill_years_list;

    for (my $i = 0; $i <= $#years_list; $i++) {
	opendir(YEAR_DIR, "$db_dir/$years_list[$i]");
	foreach my $host (readdir(YEAR_DIR))
	{
	    next if ($host !~ m/\.intf$/);
	    &summ(\%dates, $years_list[$i], $host);
	}
	closedir(YEAR_DIR);
    }

    print "<table><tr><th class='header' align='center'>No</th>\n";
    print "<th class='header' align='center'>Date</th>\n";
    print "<th class='header' align='center'>Input</th>\n";
    print "<th class='header' align='center'>Output</th></tr>\n";

    my $i;
    foreach my $date (sort keys %dates) {
        $date =~ m/^(\d{4})(\d{2})(\d{2})$/;
	printf "<tr><td class='data'>%d</td>\n", ++$i;
	print "<td class='data2'>$3.$2.$1</td>\n";
	print "<td class='data2'>" . &bytes_split($dates{$date}[0]) . "</td>\n";
	print "<td class='data2'>" . &bytes_split($dates{$date}[1]) . "</td>\n</tr>";
    }

    &print_tail;
}

sub page7 {
    my %dates;
    my @labels;
    my @input;
    my @output;

    &fill_years_list;

    for (my $i = 0; $i <= $#years_list; $i++) {
	opendir(YEAR_DIR, "$db_dir/$years_list[$i]");
	foreach my $host (readdir(YEAR_DIR))
	{
	    next if ($host !~ m/\.intf$/);
	    &summ(\%dates, $years_list[$i], $host);
	}
	closedir(YEAR_DIR);
    }

    foreach my $date (sort keys %dates) {
	$date =~ m/^(\d{4})(\d{2})(\d{2})$/;
	push (@labels, "$3.$2.$1");
	push (@input, $dates{$date}[0]/1024/1024);
	push (@output, $dates{$date}[1]/1024/1024);
    }

    my $obj = Chart::Lines->new(850, 350);
    my @data = (\@labels, \@input, \@output);

    my $title = &resolve($FORM{'host'}) . sprintf(" (%s)", ($alias{$FORM{'iface'}}) ? $alias{$FORM{'iface'}} : $FORM{'iface'});

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
	    'dataset0'		=> [255,0,0],
	    'dataset1'		=> [0,0,255]
	}
    );

    $obj->cgi_png(\@data);
}

sub page8 {
    my %dates;
    my @labels;
    my @tmp;

    &fill_years_list;

    for (my $i = 0; $i <= $#years_list; $i++) {
	&summ(\%dates, $years_list[$i], $FORM{'host'} . ".type");
    }

    foreach my $date (sort keys %dates) {
	$date =~ m/^(\d{4})(\d{2})(\d{2})$/;
	push (@labels, "$3.$2.$1");
	for (my $i = 0; $i <= $#{$dates{$date}}; $i++) {
	    push (@{$tmp[$i]}, $dates{$date}[$i]/1024/1024);
	}
    }

    my $obj = Chart::Lines->new(850, 350);
    my @data = (\@labels, @tmp);

    $obj->set (
	'title'			=> $FORM{'host'},
	'sub_title'		=> $FORM{'date'},
	'x_label'		=> "Days",
	'y_label'		=> 'Megabytes',
	'x_ticks'		=> 'vertical',
	'legend_labels'		=> ['Other','Web', 'Mail'],
	'brush_size'		=> 4,
	'grid_lines'		=> 'true',
	'grey_background'	=> 'false',
	'colors'		=> {
	    'background'	=> [255,255,255],
	    'grid_lines'	=> [230,230,230]
	}
    );

    $obj->cgi_png(\@data);
}

sub summ {
    my $ref = shift;
    my $year = shift;
    my $db = shift;
    my $host = shift;

    open(DB, "$db_dir/$year/$db");

    do {
	my $record;
	my $date_match;

	read(DB, $record, 8);
	my ($date, $num) = unpack("I2", $record);

	if ($date >= $FORM{'year1'} . $FORM{'month1'} . $FORM{'day1'} &&
		$date <= $FORM{'year2'} . $FORM{'month2'} . $FORM{'day2'}) {
	    $date_match = 1;
	}

	for (my $i = 0; $i < $num; $i++) {
	    read(DB, $record, 48);
	    my ($iface, undef, undef, undef, undef, $in_a, $in_b, $out_a, $out_b) = unpack("Z16L8", $record);

	    if ($date_match) {
		switch ($FORM{'page'}) {
		    case '1' {
			$$ref{$host}[0] += $in_b * $offset + $in_a;
			$$ref{$host}[1] += $out_b * $offset + $out_a;
		    }
		    case '2' {
			$$ref{$iface}[0] += $in_b * $offset + $in_a;
			$$ref{$iface}[1] += $out_b * $offset + $out_a;
		    }
		    case [3,4] {
			$$ref{$date}[0] += $in_b * $offset + $in_a;
			$$ref{$date}[1] += $out_b * $offset + $out_a;
		    }
		    case [5,8] {
			$$ref{$date}[$iface] += ($in_b * $offset + $in_a) + ($out_b * $offset + $out_a);
		    }
		    case [6,7] {
			if ($iface eq $FORM{'iface'}) {
			    $$ref{$date}[0] += $in_b * $offset + $in_a;
			    $$ref{$date}[1] += $out_b * $offset + $out_a;
			}
		    }
		}
	    }
	}
    } while (!eof(DB));

    close(DB);
}

sub bytes_split {
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

sub print_header {
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

sub print_tail {
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
