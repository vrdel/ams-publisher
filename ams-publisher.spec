%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

%define underscore() %(echo %1 | sed 's/-/_/g')
%define stripc() %(echo %1 | sed 's/el7.centos/el7/')
%define mydist %{stripc %{dist}}

Name:           ams-publisher
Summary:        Bridge from Sensu/Nagios to the ARGO Messaging system
Version:        0.4.1
Release:        1%{mydist}

Group:          Network/Monitoring
License:        ASL 2.0
URL:            https://github.com/ARGOeu/argo-nagios-ams-publisher
Source0:        %{name}-%{version}.tar.gz

BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch

%prep
%setup -q

%description
Bridge from Sensu/Nagios to the ARGO Messaging system

%build
%{py3_build}

%install
rm -rf $RPM_BUILD_ROOT
%{py3_install}
install --directory --mode 755 $RPM_BUILD_ROOT/%{_sysconfdir}/ams-publisher/
install --directory --mode 755 $RPM_BUILD_ROOT/%{_localstatedir}/log/ams-publisher/
install --directory --mode 755 $RPM_BUILD_ROOT/%{_localstatedir}/spool/ams-publisher/


%package -n argo-nagios-ams-publisher
Summary:   Bridge from Nagios to the ARGO Messaging system
Conflicts:     argo-sensu-ams-publisher

BuildRequires:    python3-devel
Requires:         nagios
Requires:         python3-argo-ams-library
Requires:         python3-avro
Requires:         python3-dirq
Requires:         python3-messaging
%if 0%{?el7}
Requires:         python36-pytz
%endif
%if 0%{?el9}
Requires:         python3-pytz
%endif
Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd

%description -n argo-nagios-ams-publisher
Bridge from Nagios to the ARGO Messaging system

%files -n argo-nagios-ams-publisher
%defattr(-,root,root,-)
%{_bindir}/ams-metric-to-queue
%{_bindir}/ams-publisherd
%config(noreplace) %{_sysconfdir}/ams-publisher/ams-publisher-nagios.conf
%config(noreplace) %{_sysconfdir}/ams-publisher/metric_data.avsc
%dir %{python3_sitelib}/ams_publisher
%{python3_sitelib}/ams_publisher/*.py
%{python3_sitelib}/ams_publisher/__pycache__/
%{python3_sitelib}/*.egg-info
%{_unitdir}/ams-publisher-nagios.service
%defattr(-,nagios,nagios,-)
%dir %{_localstatedir}/log/ams-publisher/
%dir %{_localstatedir}/spool/ams-publisher/

%post -n argo-nagios-ams-publisher
%systemd_postun_with_restart ams-publisher-nagios.service

%preun -n argo-nagios-ams-publisher
%systemd_preun ams-publisher-nagios.service


%package -n argo-sensu-ams-publisher
Summary:   Bridge from Sensu to the ARGO Messaging system
Conflicts: argo-nagios-ams-publisher

BuildRequires:    python3-devel
Requires:         sensu-go-backend
Requires:         python3-argo-ams-library
Requires:         python3-avro
Requires:         python3-dirq
Requires:         python3-messaging
%if 0%{?el7}
Requires:         python36-pytz
%endif
%if 0%{?el9}
Requires:         python3-pytz
%endif
Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd

%description -n argo-sensu-ams-publisher
Bridge from Sensu to the ARGO Messaging system

%files -n argo-sensu-ams-publisher
%defattr(-,root,root,-)
%{_bindir}/ams-metric-to-queue
%{_bindir}/ams-publisherd
%config(noreplace) %{_sysconfdir}/ams-publisher/ams-publisher-sensu.conf
%config(noreplace) %{_sysconfdir}/ams-publisher/metric_data.avsc
%dir %{python3_sitelib}/ams_publisher
%{python3_sitelib}/ams_publisher/*.py
%{python3_sitelib}/ams_publisher/__pycache__/
%{python3_sitelib}/*.egg-info
%{_unitdir}/ams-publisher-sensu.service
%defattr(-,sensu,sensu,-)
%dir %{_localstatedir}/log/ams-publisher/
%dir %{_localstatedir}/spool/ams-publisher/

%post -n argo-sensu-ams-publisher
%systemd_postun_with_restart ams-publisher-sensu.service

%preun -n argo-sensu-ams-publisher
%systemd_preun ams-publisher-sensu.service


%clean
rm -rf $RPM_BUILD_ROOT

%changelog
* Mon Mar 18 2024 Daniel Vrcic <dvrcic@srce.hr> - 0.4.1-1%{?dist}
- refine spec by varying pytz dependency based on whether we're building on Centos7 or Rocky9
* Thu Sep 1 2022 Daniel Vrcic <dvrcic@srce.hr> - 0.4.0-1%{?dist}
- ARGO-3754 Build two RPMS, Nagios and Sensu with appropriate runtime permission settings
- ARGO-3825 List requires explicitly for each ams-publisher package
* Mon Feb 1 2021 Daniel Vrcic <dvrcic@srce.hr> - 0.3.9-1%{?dist}
- ARGO-2855 ams-publisher py3 switch
- ARGO-2929 Let systemd handle runtime directory
* Thu Oct  8 2020 Daniel Vrcic <dvrcic@srce.hr> - 0.3.8-1%{?dist}
- remove leftovers from erroneous SIGHUP handling
* Wed Jul  8 2020 Daniel Vrcic <dvrcic@srce.hr> - 0.3.7-1%{?dist}
- ARGO-2378 RPM post install should restart service not stop it
- ARGO-844 Complete README for ams-publisher
* Tue Mar 31 2020 Daniel Vrcic <dvrcic@srce.hr> - 0.3.6-1%{?dist}
- ARGO-2224 Local delivery cache tool should pass non-ascii characters
* Tue Apr 23 2019 Daniel Vrcic <dvrcic@srce.hr> - 0.3.5-2%{?dist}
- regression fix to include site name in `site` field of notification
* Wed Apr 17 2019 Daniel Vrcic <dvrcic@srce.hr> - 0.3.5-1%{?dist}
- ARGO-1726 Pass site name in metric results
* Wed Mar 6 2019 Daniel Vrcic <dvrcic@srce.hr> - 0.3.4-1%{?dist}
- verbose log messages for errors not handled in argo-ams-library
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
