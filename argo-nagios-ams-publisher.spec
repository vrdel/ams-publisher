%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

%define underscore() %(echo %1 | sed 's/-/_/g')

Name:           argo-nagios-ams-publisher
Version:        0.1.0
Release:        2%{?dist}
Summary:        Bridge from Nagios to the ARGO Messaging system

Group:          Network/Monitoring
License:        ASL 2.0  
URL:            https://github.com/ARGOeu/argo-nagios-ams-publisher
Source0:        %{name}-%{version}.tar.gz 

BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch 
BuildRequires:  python2-devel
Requires:       python-psutil >= 4.3
Requires:       python-daemon
Requires:       python-argparse
Requires:       python-messaging
Requires:       python-dirq
Requires:       avro
Requires:       argo-ams-library

%description
Bridge from Nagios to the ARGO Messaging system 

%prep
%setup -q

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --skip-build --root $RPM_BUILD_ROOT --record=INSTALLED_FILES
install --directory --mode 755 $RPM_BUILD_ROOT/%{_sysconfdir}/%{name}/
install --directory --mode 755 $RPM_BUILD_ROOT/%{_localstatedir}/log/%{name}/
install --directory --mode 755 $RPM_BUILD_ROOT/%{_localstatedir}/spool/%{name}/metrics/
install --directory --mode 755 $RPM_BUILD_ROOT/%{_localstatedir}/spool/%{name}/alarms/
install --directory --mode 755 $RPM_BUILD_ROOT/%{_localstatedir}/run/%{name}/

%files -f INSTALLED_FILES
%defattr(-,root,root,-)
%dir %{python_sitelib}/%{underscore %{name}}
%{python_sitelib}/%{underscore %{name}}/*.py[co]
%defattr(-,nagios,nagios,-)
%dir %{_localstatedir}/log/%{name}/
%dir %{_localstatedir}/run/%{name}/
%dir %{_localstatedir}/spool/%{name}/metrics/
%dir %{_localstatedir}/spool/%{name}/alarms/

%post
/sbin/chkconfig --add ams-publisher 
if [ "$1" = 2 ]; then
  /sbin/service ams-publisher stop > /dev/null 2>&1
fi

%clean
rm -rf $RPM_BUILD_ROOT

%preun
if [ "$1" = 0 ]; then
  /sbin/service ams-publisher stop > /dev/null 2>&1
  /sbin/chkconfig --del ams-publisher 
fi
exit 0

%postun
if [ "$1" = 0 ]; then
  rm -rf %{_localstatedir}/run/%{name}/
fi
exit 0


%pre
if ! /usr/bin/id nagios &>/dev/null; then
    /usr/sbin/useradd -r -m -d /var/log/nagios -s /bin/sh -c "nagios" nagios || \
        logger -t nagios/rpm "Unexpected error adding user \"nagios\". Aborting installation."
fi
if ! /usr/bin/getent group nagiocmd &>/dev/null; then
    /usr/sbin/groupadd nagiocmd &>/dev/null || \
        logger -t nagios/rpm "Unexpected error adding group \"nagiocmd\". Aborting installation."
fi

%changelog
* Wed Mar 1 2017 Daniel Vrcic <dvrcic@srce.hr> - 0.1.0-2%{?dist}
- added missing queue spools
- added missing spec dependancies
* Wed Feb 15 2017 Daniel Vrcic <dvrcic@srce.hr> - 0.1.0-1%{?dist}
- first version 
