Name: trafcount
Version: 7
Release: 1.NSYS
Group: Applications/Internet
Summary: Multiple Interfaces Traffic Counter
License: GPL
Source0: %{name}-%{version}.tar.gz
Patch0: %{name}-7-centos.patch
BuildRoot: /var/tmp/%{name}-root
BuildRequires: iptables-devel net-snmp-libs
Requires: httpd iptables

%description

%prep
%setup -q
%patch0 -p1

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
install -m 644 sarg.css graph.png datetime.png $RPM_BUILD_ROOT/var/www/trafcount

%files
%config(noreplace) %{_sysconfdir}/cron.d/trafcount
%config(noreplace) %{_sysconfdir}/httpd/conf.d/trafcount.conf
/usr/sbin/trafcount
/var/lib/trafcount
/var/www/trafcount

%clean
[ $RPM_BUILD_ROOT != "/" ] && rm -rf $RPM_BUILD_ROOT

%changelog
