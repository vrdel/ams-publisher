%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

%define underscore() %(echo %1 | sed 's/-/_/g')

Name:           argo-nagios-ams-publisher
Version:        0.2.0
Release:        1%{?dist}
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
%config(noreplace) %{_sysconfdir}/%{name}/ams-publisher.conf 
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
* Mon Jun 5 2017 Daniel Vrcic <dvrcic@srce.hr> - 0.2.0-1%{?dist}
- ARGO-797 argo-nagios-ams-publisher overwrites configuration
- ARGO-802 Singleton config object with shared config options
- ARGO-803 Refactor publisher class
- ARGO-815 Sent number of messages reported incorrectly
- ARGO-826 Pick up only HARD states
* Thu Apr 27 2017 Daniel Vrcic <dvrcic@srce.hr> - 0.1.3-1%{?dist}
- ARGO-788 Skip empty files/messages 
* Thu Mar 30 2017 Daniel Vrcic <dvrcic@srce.hr> - 0.1.2-1%{?dist}
- ARGO-764 Add url_history and url_help message fields for alarms 
* Tue Mar 14 2017 Daniel Vrcic <dvrcic@srce.hr> - 0.1.1-1%{?dist}
- ARGO-732 Structure the body of alarm message as JSON object 
* Wed Mar 1 2017 Daniel Vrcic <dvrcic@srce.hr> - 0.1.0-3%{?dist}
- timestamp is automatically generated and not taken from nagios 
* Wed Mar 1 2017 Daniel Vrcic <dvrcic@srce.hr> - 0.1.0-2%{?dist}
- added missing queue spools
- added missing spec dependancies
* Wed Feb 15 2017 Daniel Vrcic <dvrcic@srce.hr> - 0.1.0-1%{?dist}
- first version 
