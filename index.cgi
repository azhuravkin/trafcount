#!/usr/bin/perl

use bignum;

my $offset = 1 << 32;

my $db_dir = "/var/lib/trafcount";

&parse_form;

if (($FORM{'host'} ne "") && ($FORM{'intf'} ne "") && ($FORM{'date'} ne "")) {
    &print_stats($FORM{'host'}, $FORM{'intf'}, $FORM{'date'});
} elsif (($FORM{'host'} ne "") && ($FORM{'intf'} ne "")) {
    &print_date($FORM{'host'}, $FORM{'intf'});
} elsif ($FORM{'host'} ne "") {
    &print_intf($FORM{'host'});
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
<tbody><tr></tr>
_end_
}

sub print_host()
{
    my $host;
    my @host;
    my $i = 0;

    opendir(DBDIR, $db_dir);
    foreach my $file (readdir(DBDIR))
    {
	next unless ((-d "$db_dir/$file") && ($file !~ m/^\./));
	$host[$i++] = $file;
    }
    closedir(DBDIR);

    &print_header;

    print '<tr><th class="header" align="center">No</th>';
    print '<th class="header" align="center">Hostname</th></tr>';

    $i = 0;
    foreach $host (sort @host)
    {
	$i++;
	print "<tr><td class=\"data2\" align=\"right\">$i</td>\n";
	print "<td class=\"data2\" align=\"left\"><font color=\"blue\"><a href=\"?host=$host\">$host</a></font></td></tr>\n";
    }
}

sub print_intf()
{
    my $host = shift;
    my $intf;
    my @intf;
    my $i = 0;

    opendir(DBDIR, "$db_dir/$host");
    foreach my $file (readdir(DBDIR))
    {
	next if ($file !~ m/^(.*)\.db$/);
	$intf[$i++] = $1;
    }
    closedir(DBDIR);

    &print_header;

    print '<tr><th class="header" align="center">No</th>';
    print '<th class="header" align="center">Interface</th></tr>';

    $i = 0;
    foreach $intf (sort @intf)
    {
	$i++;
	print "<tr><td class=\"data2\" align=\"right\">$i</td>\n";
	print "<td class=\"data2\" align=\"left\"><font color=\"blue\"><a href=\"?host=$host&intf=$intf\">$intf</a></font></td></tr>\n";
    }
}

sub print_date()
{
    my $host = shift;
    my $intf = shift;
    my $record;
    my $i = 0;
    my %bytes_in;
    my %bytes_out;

    &print_header;

    print '<tr><th class="header" align="center">No</th>';
    print '<th class="header" align="center">Date</th>';
    print '<th class="header" align="center">Interface</th>';
    print '<th class="header" align="center">In Bytes</th>';
    print '<th class="header" align="center">Out Bytes</th></tr>';

    open(DB, "$db_dir/$host/${intf}.db");

    do {
	read(DB, $record, 28);
        my ($date, undef, undef, $in_a, $in_b, $out_a, $out_b) = unpack("IL6", $record);

	if ($date) {
	    $date =~ s/^(\d{4})(\d{2})\d{2}$/$1$2/;

	    $bytes_in{$date} += $in_b * $offset + $in_a;
	    $bytes_out{$date} += $out_b * $offset + $out_a;
	}
    } while (!eof(DB));

    close(DB);

    foreach $date (reverse sort keys %bytes_in) {
	$i++;
	$date =~ m/^(\d{4})(\d{2})$/;

	print "<tr><td class=\"data2\" align=\"right\">$i</td>\n";
	print "<td class=\"data2\" align=\"right\"><font color=\"blue\"><a href=\"?host=$host&intf=$intf&date=$date\">$2.$1</a></font></td>\n";
	print "<td class=\"data2\" align=\"left\">$intf</td>\n";
	print "<td class=\"data2\" align=\"left\">" . &bytes_split($bytes_in{$date}) . "</td>\n";
	print "<td class=\"data2\" align=\"left\">" . &bytes_split($bytes_out{$date}) . "</td>\n";
    }
}

sub print_stats()
{
    my $host = shift;
    my $intf = shift;
    my $monthly = shift;
    my $record;
    my $i = 0;
    my %bytes_in;
    my %bytes_out;

    &print_header;

    print '<tr><th class="header" align="center">No</th>';
    print '<th class="header" align="center">Date</th>';
    print '<th class="header" align="center">Interface</th>';
    print '<th class="header" align="center">In Bytes</th>';
    print '<th class="header" align="center">Out Bytes</th></tr>';

    open(DB, "$db_dir/$host/${intf}.db");

    do {
	read(DB, $record, 28);
	my ($date, undef, undef, $in_a, $in_b, $out_a, $out_b) = unpack("IL6", $record);

	if ($date) {
	    $date =~ m/^(\d{4})(\d{2})\d{2}$/;
	    if ("$1$2" eq $monthly) {
		$bytes_in{$date} = $in_b * $offset + $in_a;
		$bytes_out{$date} = $out_b * $offset + $out_a;
	    }
	}
    } while (!eof(DB));

    close(DB);

    foreach $record (sort keys %bytes_in) {
        $record =~ m/^(\d{4})(\d{2})(\d{2})$/;
	$i++;

	print "<tr><td class=\"data2\" align=\"right\">$i</td>\n";
	print "<td class=\"data2\" align=\"left\">$3.$2.$1</td>\n";
	print "<td class=\"data2\" align=\"left\">$intf</td>\n";
	print "<td class=\"data2\" align=\"left\">" . &bytes_split($bytes_in{$record}) . "</td>\n";
	print "<td class=\"data2\" align=\"left\">" . &bytes_split($bytes_out{$record}) . "</td></tr>\n";
    }
}

sub parse_form {
    # Get the input
    if ($ENV{'REQUEST_METHOD'} eq "POST") { read(STDIN, $buffer, $ENV{'CONTENT_LENGTH'}); }
    if ($ENV{'REQUEST_METHOD'} eq "GET") { $buffer = $ENV{'QUERY_STRING'}; }

    # Split the name-value pairs
    @pairs = split(/&/, $buffer);

    foreach $pair (@pairs) {
	($name, $value) = split(/=/, $pair);

        # Un-Webify plus signs and %-encoding
        $value =~ tr/+/ /;
        $value =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;

        $FORM{$name} = $value;
    }
}
