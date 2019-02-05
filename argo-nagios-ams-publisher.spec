%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

%define underscore() %(echo %1 | sed 's/-/_/g')
%define stripc() %(echo %1 | sed 's/el7.centos/el7/')

%if 0%{?el7:1}
%define mydist %{stripc %{dist}}
%else
%define mydist %{dist}
%endif

Name:           argo-nagios-ams-publisher
Version:        0.3.3
Release:        1%{mydist}
Summary:        Bridge from Nagios to the ARGO Messaging system

Group:          Network/Monitoring
License:        ASL 2.0  
URL:            https://github.com/ARGOeu/argo-nagios-ams-publisher
Source0:        %{name}-%{version}.tar.gz 

BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch 
BuildRequires:  python-devel
Requires:       argo-ams-library
Requires:       avro
Requires:       python-argparse
Requires:       python-daemon
Requires:       python-dirq
Requires:       python-messaging
Requires:       pytz

%if 0%{?el7:1}
Requires:       python2-psutil >= 4.3
%else
Requires:       python-psutil >= 4.3
%endif

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
%config(noreplace) %{_sysconfdir}/%{name}/metric_data.avsc
%dir %{python_sitelib}/%{underscore %{name}}
%{python_sitelib}/%{underscore %{name}}/*.py[co]
%defattr(-,nagios,nagios,-)
%dir %{_localstatedir}/log/%{name}/
%attr(0755,nagios,nagios) %dir %{_localstatedir}/run/%{name}/
%dir %{_localstatedir}/spool/%{name}/

%post
%if 0%{?el7:1}
%systemd_post ams-publisher.service
%else
/sbin/chkconfig --add ams-publisher 
if [ "$1" = 2 ]; then
  /sbin/service ams-publisher stop > /dev/null 2>&1
fi
%endif

%clean
rm -rf $RPM_BUILD_ROOT

%preun
if [ "$1" = 0 ]; then
%if 0%{?el7:1}
%systemd_preun ams-publisher.service
%else
	/sbin/service ams-publisher stop > /dev/null 2>&1
	/sbin/chkconfig --del ams-publisher 
%endif
fi
exit 0

%postun
%if 0%{?el7:1}
%systemd_postun_with_restart ams-publisher.service
%endif 
if [ "$1" = 0 ]; then
	test -d  %{_localstatedir}/run/%{name}/ && rm -rf %{_localstatedir}/run/%{name}/
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
* Tue Feb  5 2019 Daniel Vrcic <dvrcic@srce.hr> - 0.3.3-1%{?dist}
- ARGO-1624 Catch all exceptions and warnings from AMS
* Thu Nov  8 2018 Daniel Vrcic <dvrcic@srce.hr> - 0.3.2-1%{?dist}
- ARGO-1429 Improved msg counter stats for probe testing purposes
- ARGO-1408 Ensure correct permissions on pidfile directory
- ARGO-1348 Descriptive error in case delivery cache tool is called with queue
  path not specified in configs
* Tue Jun 19 2018 Daniel Vrcic <dvrcic@srce.hr> - 0.3.1-1%{?dist}
- ARGO-1250 Inspection local socket is left with root permissions 
- ARGO-1147 AMS publisher to add optional field
- ARGO-986 Purger should not try to remove non-existing cache msg
* Tue Mar 27 2018 Daniel Vrcic <dvrcic@srce.hr> - 0.3.0-1%{?dist}
- ARGO-1084 Connection settings per topic publisher
- ARGO-1023 Send messages to prod and devel AMS instance in parallel
- ARGO-1055 Last time stats report not updated
- ARGO-1051 Ensure service stop called on system shutdown
- ARGO-1004 UTC timestamp instead of localtime for dispatched results
- ARGO-978 Add systemd init script
- ARGO-806 AMS Publisher nagios testing method for upcoming probe
* Wed Dec 20 2017 Daniel Vrcic <dvrcic@srce.hr> - 0.2.1-1%{?dist}
- Centos 7 code fixes and spec update
- ARGO-930 Service stop should not depend on successful config parse
- ARGO-700 Delay each msg publish try in case of connection problems
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
