Name: trafcount
Version: 5
Release: NSYS
Group: Applications/Internet
Summary: Multiple Interfaces Traffic Counter
License: GPL
Source0: %{name}-%{version}.tar.gz
BuildRoot: /var/tmp/%{name}-root
BuildRequires: net-snmp-devel net-snmp-libs
Requires: httpd net-snmp-libs

%description

%prep
%setup

%install
make clean all

%{__mkdir_p} $RPM_BUILD_ROOT/usr/sbin
%{__mkdir_p} $RPM_BUILD_ROOT/var/lib/trafcount
%{__mkdir_p} $RPM_BUILD_ROOT%{_sysconfdir}/cron.d
%{__mkdir_p} $RPM_BUILD_ROOT%{_sysconfdir}/httpd/conf.d
%{__mkdir_p} $RPM_BUILD_ROOT/var/www/trafcount

install -m 755 trafcount $RPM_BUILD_ROOT/usr/sbin
install -m 644 cron $RPM_BUILD_ROOT%{_sysconfdir}/cron.d/trafcount
install -m 644 trafcount.conf $RPM_BUILD_ROOT%{_sysconfdir}/httpd/conf.d
install -m 755 index.cgi $RPM_BUILD_ROOT/var/www/trafcount
install -m 644 sarg.css graph.png $RPM_BUILD_ROOT/var/www/trafcount

%files
%config(noreplace) %{_sysconfdir}/cron.d/trafcount
%config(noreplace) %{_sysconfdir}/httpd/conf.d/trafcount.conf
/usr/sbin/trafcount
/var/lib/trafcount
/var/www/trafcount/*

%clean
[ $RPM_BUILD_ROOT != "/" ] && rm -rf $RPM_BUILD_ROOT

%changelog
* Sun May 9 2009 Juravkin Alexander <rinus@nsys.by>
- Support graphics for monthly statistic.

* Fri Aug 15 2008 Juravkin Alexander <rinus@nsys.by>
- Build
