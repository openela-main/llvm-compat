%global maj_ver 17
%global min_ver 0
%global patch_ver 6
%global baserelease 3

# Limit build jobs on ppc64 systems to avoid running out of memory.
%global _smp_mflags -j8

%global install_prefix %{_libdir}/llvm%{maj_ver}
%global pkg_libdir %{install_prefix}/lib/

Name:		llvm-compat
Version:	%{maj_ver}.%{min_ver}.%{patch_ver}
Release:	%{baserelease}%{?dist}
Summary:	The Low Level Virtual Machine

License:	NCSA
URL:		http://llvm.org
Source0:	https://github.com/llvm/llvm-project/releases/download/llvmorg-%{version}/llvm-%{version}.src.tar.xz
Source1:	https://github.com/llvm/llvm-project/releases/download/llvmorg-%{version}/clang-%{version}.src.tar.xz
Source2:	https://github.com/llvm/llvm-project/releases/download/llvmorg-%{version}/cmake-%{version}.src.tar.xz

# LLVM Patches:

# Clang Patches:
Patch102:	0003-PATCH-Make-funwind-tables-the-default-on-all-archs.patch

# Not Upstream
Patch115:	0003-PATCH-clang-Don-t-install-static-libraries.patch


BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:	cmake
BuildRequires:	zlib-devel
BuildRequires:  libffi-devel
BuildRequires:	ncurses-devel
BuildRequires:	multilib-rpm-config
BuildRequires:	ninja-build
# This pulls in /usr/bin/python3
BuildRequires:	python3-devel

%ifarch %{valgrind_arches}
# Enable extra functionality when run the LLVM JIT under valgrind.
BuildRequires:  valgrind-devel
%endif

Requires:	%{name}-libs%{?_isa} = %{version}-%{release}

%description
LLVM is a compiler infrastructure designed for compile-time, link-time,
runtime, and idle-time optimization of programs from arbitrary programming
languages. The compiler infrastructure includes mirror sets of programming
tools as well as libraries with equivalent functionality.

%package libs
Summary:	LLVM shared libraries
#Obsoletes:	clang-libs = %{version}
Obsoletes:	llvm-libs = %{version}

%description libs
Shared libraries for the LLVM compiler infrastructure.

%package devel
Summary:	Libraries and header files for LLVM

Requires:	%{name}%{?_isa} = %{version}-%{release}
Requires:	%{name}-libs%{?_isa} = %{version}-%{release}

%description devel
This package contains library and header files needed to develop new native
programs that use the LLVM infrastructure.


%prep
%setup -T -q -b 2 -n cmake-%{version}.src
cd ..
mv cmake-%{version}.src cmake

%setup -T -q -b 1 -n clang-%{version}.src
%autopatch -m100 -p2
cd ..
mv clang-%{version}.src clang

%setup -q -n llvm-%{version}.src
%autopatch -M100 -p2


%build

%ifarch s390 %ix86
# Decrease debuginfo verbosity to reduce memory consumption during final library linking
%global optflags %(echo %{optflags} | sed 's/-g /-g1 /')
%endif

cd ..

mkdir llvm-build
pushd llvm-build

# force off shared libs as cmake macros turns it on.
%cmake ../llvm-%{version}.src -G Ninja \
	-DBUILD_SHARED_LIBS:BOOL=OFF \
	-DCMAKE_SKIP_INSTALL_RPATH:BOOL=ON \
%ifarch ppc64le
	-DCMAKE_BUILD_TYPE=Release \
%else
	-DCMAKE_BUILD_TYPE=RelWithDebInfo \
%endif
%ifarch s390 %ix86
	-DCMAKE_C_FLAGS_RELWITHDEBINFO="%{optflags} -DNDEBUG" \
	-DCMAKE_CXX_FLAGS_RELWITHDEBINFO="%{optflags} -DNDEBUG" \
%endif
	\
	-DLLVM_TARGETS_TO_BUILD="X86;AMDGPU;PowerPC;NVPTX;SystemZ;AArch64;ARM;Mips;BPF;WebAssembly" \
	-DLLVM_DISTRIBUTION_COMPONENTS="LLVM;libclang;llvm-config;llvm-headers;libclang-headers;cmake-exports;clang-cmake-exports;clang-headers;clang-cpp;clang-resource-headers" \
	-DLLVM_ENABLE_LIBCXX:BOOL=OFF \
	-DLLVM_ENABLE_ZLIB:BOOL=ON \
	-DLLVM_ENABLE_FFI:BOOL=ON \
	-DLLVM_ENABLE_RTTI:BOOL=ON \
	-DLLVM_BUILD_LLVM_DYLIB:BOOL=ON \
	-DLLVM_DYLIB_EXPORT_ALL:BOOL=ON \
	-DLLVM_LINK_LLVM_DYLIB:BOOL=ON \
	-DLLVM_INCLUDE_TESTS=OFF \
	-DLLVM_INCLUDE_BENCHMARKS=OFF \
	-DLLVM_ENABLE_PROJECTS="clang"  \
	-DCMAKE_INSTALL_PREFIX=%{install_prefix}


DESTDIR=%{buildroot} %__ninja %__ninja_common_opts distribution

popd

%install
cd ..

DESTDIR=%{buildroot} %__ninja %__ninja_common_opts -l 8 -C llvm-build install-distribution

# Create ld.so.conf.d entry
mkdir -p %{buildroot}%{_sysconfdir}/ld.so.conf.d
cat >> %{buildroot}%{_sysconfdir}/ld.so.conf.d/%{name}-%{_arch}.conf << EOF
%{pkg_libdir}
EOF

%check

%post libs -p /sbin/ldconfig
%postun libs -p /sbin/ldconfig

%files

%files libs
%config(noreplace) %{_sysconfdir}/ld.so.conf.d/%{name}-%{_arch}.conf
%{pkg_libdir}/libLLVM-%{maj_ver}.so
%{pkg_libdir}/libLLVM-%{version}.so
%{pkg_libdir}/libclang*.so.*
%{pkg_libdir}/clang/%{maj_ver}/

%files devel
%dir %{install_prefix}/bin/
%{install_prefix}/include/
%{install_prefix}/bin/llvm-config
%{pkg_libdir}/cmake/llvm/
%{pkg_libdir}/cmake/clang/
%{pkg_libdir}/libLLVM.so
%{pkg_libdir}/libclang-cpp.so
%{pkg_libdir}/libclang.so

%changelog
* Fri Aug 16 2024 Tom Stellard <tstellar@redhat.com> - 17.0.6-3
- Re-enable debuginfo on ppc64le

* Tue Jul 30 2024 Tom Stellard <tstellar@redhat.com> - 17.0.6-2
- Add devel package

* Fri Apr 19 2024 Tom Stellard <tstellar@redhat.com> - 17.0.6-1
- 17.0.6 Release

* Tue Oct 17 2023 Nikita Popov <npopov@redhat.com> - 16.0.6-4
- Use install targets for clang as well

* Mon Oct 16 2023 Nikita Popov <npopov@redhat.com> - 16.0.6-3
- Only skip install rpath

* Fri Oct 13 2023 Nikita Popov <npopov@redhat.com> - 16.0.6-2
- Disable rpath

* Wed Oct 04 2023 Nikita Popov <npopov@redhat.com> - 16.0.6-1
- 16.0.6 Release

* Fri Apr 28 2023 Tom Stellard <tstellar@redhat.com> - 15.0.7-1
- 15.0.7 Release

* Tue Oct 18 2022 Tom Stellard <tstellar@redhat.com> - 14.0.6-1
- 14.0.6 Release

* Thu Apr 07 2022 Timm Bäder <tbaeder@redhat.com> - 13.0.1-1
- Update to 13.0.1

* Tue Nov 23 2021 Tom Stellard <tstellar@redhat.com> - 12.0.1-4
- Add libclang-cpp.so to package

* Mon Nov 01 2021 Tom Stellard <tstellar@redhat.com> - 12.0.1-3
- Enable WebAssembly target

* Fri Oct 15 2021 Tom Stellard <tstellar@redhat.com> - 12.0.1-2
- 12.0.1 Release

* Tue Jun 1 2021 sguelton@redhat.com - 11.0.1-1
- 11.0.1 Release

* Fri Sep 25 2020 sguelton@redhat.com - 10.0.1-1
- 10.0.1 Release

* Tue Apr 7 2020 sguelton@redhat.com - 9.0.0-1
- 9.0.0 Release

* Mon Sep 30 2019 Tom Stellard <tstellar@redhat.com> - 8.0.1-2
- Limit number of build threads using -l option for ninja

* Mon Sep 30 2019 Tom Stellard <tstellar@redhat.com> - 8.0.1-1
- 8.0.1 Release

* Tue May 14 2019 sguelton@redhat.com - 7.0.1-8
- Mark llvm-libs and clang-libs = 7 as obsoletes

* Mon May 13 2019 sguelton@redhat.com - 7.0.1-7
- Mark llvm-libs and clang-libs < 8 as conflics instead of obsoletes

* Mon May 13 2019 sguelton@redhat.com - 7.0.1-6
- Declare obsoletes llvm-libs-7

* Mon May 13 2019 sguelton@redhat.com - 7.0.1-5
- Declare obsoletes clang-libs-7

* Wed May 1 2019 sguelton@redhat.com - 7.0.1-4
- Ship libclang.so

* Fri Apr 19 2019 Tom Stellard <tstellar@redhat.com> - 7.0.1-3
- Backport r342725 from trunk

* Sat Apr 13 2019 Tom Stellard <tstellar@redhat.com> - 7.0.1-2
- Backport r341969 from LLVM trunk

* Fri Dec 14 2018 Tom Stellard <tstellar@redhat.com> - 7.0.1-1
- 7.0.1 Release

* Thu Dec 13 2018 Tom Stellard <tstellar@redhat.com> - 7.0.1-0.5.rc3
- Drop compat libs

* Wed Dec 12 2018 Tom Stellard <tstellar@redhat.com> - 7.0.1-0.4.rc3
- Fix ambiguous python shebangs

* Tue Dec 11 2018 Tom Stellard <tstellar@redhat.com> - 7.0.1-0.3.rc3
- Disable threading in thinLTO

* Tue Dec 11 2018 Tom Stellard <tstellar@redhat.com> - 7.0.1-0.2.rc3
- Update cmake options for compat build

* Mon Dec 10 2018 Tom Stellard <tstellar@redhat.com> - 7.0.1-0.1.rc3
- 7.0.1-rc3 Release

* Fri Dec 07 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-14
- Don't build llvm-test on i686

* Thu Dec 06 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-13
- Fix build when python2 is not present on system

* Tue Nov 06 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-12
- Fix multi-lib installation of llvm-devel

* Tue Oct 23 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-11
- Add sub-packages for testing

* Mon Oct 01 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-10
- Drop scl macros

* Tue Aug 28 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-9
- Drop libedit dependency

* Tue Aug 14 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-8
- Only enabled valgrind functionality on arches that support it

* Mon Aug 13 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-7
- BuildRequires: python3-devel

* Mon Aug 06 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-6
- Backport fixes for rhbz#1610053, rhbz#1562196, rhbz#1595996

* Mon Aug 06 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-5
- Fix ld.so.conf.d path in files list

* Sat Aug 04 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-4
- Fix ld.so.conf.d path

* Fri Aug 03 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-3
- Install ld.so.conf so llvm libs are in the library search path

* Wed Jul 25 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-2
- Re-enable doc package now that BREW-2381 is fixed

* Tue Jul 10 2018 Tom Stellard <tstellar@redhat.com> - 6.0.1-1
- 6.0.1 Release

* Mon Jun 04 2018 Tom Stellard <tstellar@redhat.com> - 5.0.1-13
- Limit build jobs on ppc64 to avoid OOM errors

* Sat Jun 02 2018 Tom Stellard <tstellar@redhat.com> - 5.0.1-12
- Switch to python3-sphinx

* Thu May 31 2018 Tom Stellard <tstellar@redhat.com> - 5.0.1-11
- Remove conditionals to enable building only the llvm-libs package, we don't
  needs these for module builds.

* Wed May 23 2018 Tom Stellard <tstellar@redhat.com> - 5.0.1-10
- Add BuildRequires: libstdc++-static
- Resolves: #1580785

* Wed Apr 04 2018 Tom Stellard <tstellar@redhat.com> - 5.0.1-9
- Add conditionals to enable building only the llvm-libs package

* Tue Apr 03 2018 Tom Stellard <tstellar@redhat.com> - 5.0.1-8
- Drop BuildRequires: libstdc++-static this package does not exist in RHEL8

* Tue Mar 20 2018 Tilmann Scheller <tschelle@redhat.com> - 5.0.1-7
- Backport fix for rhbz#1558226 from trunk

* Tue Mar 06 2018 Tilmann Scheller <tschelle@redhat.com> - 5.0.1-6
- Backport fix for rhbz#1550469 from trunk

* Thu Feb 22 2018 Tom Stellard <tstellar@redhat.com> - 5.0.1-5
- Backport some retpoline fixes

* Tue Feb 06 2018 Tom Stellard <tstellar@redhat.com> - 5.0.1-4
- Backport retpoline support

* Mon Jan 29 2018 Tom Stellard <tstellar@redhat.com> - 5.0.1-3
- Backport r315279 to fix an issue with rust

* Mon Jan 15 2018 Tom Stellard <tstellar@redhat.com> - 5.0.1-2
- Drop ExculdeArch: ppc64

* Mon Jan 08 2018 Tom Stellard <tstellar@redhat.com> - 5.0.1-1
- 5.0.1 Release

* Thu Jun 22 2017 Tom Stellard <tstellar@redhat.com> - 4.0.1-3
- Fix Requires for devel package again.

* Thu Jun 22 2017 Tom Stellard <tstellar@redhat.com> - 4.0.1-2
- Fix Requires for llvm-devel

* Tue Jun 20 2017 Tom Stellard <tstellar@redhat.com> - 4.0.1-1
- 4.0.1 Release

* Mon Jun 05 2017 Tom Stellard <tstellar@redhat.com> - 4.0.0-5
- Build for llvm-toolset-7 rename

* Mon May 01 2017 Tom Stellard <tstellar@redhat.com> - 4.0.0-4
- Remove multi-lib workarounds

* Fri Apr 28 2017 Tom Stellard <tstellar@redhat.com> - 4.0.0-3
- Fix build with llvm-toolset-4 scl

* Mon Apr 03 2017 Tom Stellard <tstellar@redhat.com> - 4.0.0-2
- Simplify spec with rpm macros.

* Thu Mar 23 2017 Tom Stellard <tstellar@redhat.com> - 4.0.0-1
- LLVM 4.0.0 Final Release

* Wed Mar 22 2017 tstellar@redhat.com - 3.9.1-6
- Fix %%postun sep for -devel package.

* Mon Mar 13 2017 Tom Stellard <tstellar@redhat.com> - 3.9.1-5
- Disable failing tests on ARM.

* Sun Mar 12 2017 Peter Robinson <pbrobinson@fedoraproject.org> 3.9.1-4
- Fix missing mask on relocation for aarch64 (rhbz 1429050)

* Wed Mar 01 2017 Dave Airlie <airlied@redhat.com> - 3.9.1-3
- revert upstream radeonsi breaking change.

* Thu Feb 23 2017 Josh Stone <jistone@redhat.com> - 3.9.1-2
- disable sphinx warnings-as-errors

* Fri Feb 10 2017 Orion Poplawski <orion@cora.nwra.com> - 3.9.1-1
- llvm 3.9.1

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 3.9.0-8
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Tue Nov 29 2016 Josh Stone <jistone@redhat.com> - 3.9.0-7
- Apply backports from rust-lang/llvm#55, #57

* Tue Nov 01 2016 Dave Airlie <airlied@gmail.com - 3.9.0-6
- rebuild for new arches

* Wed Oct 26 2016 Dave Airlie <airlied@redhat.com> - 3.9.0-5
- apply the patch from -4

* Wed Oct 26 2016 Dave Airlie <airlied@redhat.com> - 3.9.0-4
- add fix for lldb out-of-tree build

* Mon Oct 17 2016 Josh Stone <jistone@redhat.com> - 3.9.0-3
- Apply backports from rust-lang/llvm#47, #48, #53, #54

* Sat Oct 15 2016 Josh Stone <jistone@redhat.com> - 3.9.0-2
- Apply an InstCombine backport via rust-lang/llvm#51

* Wed Sep 07 2016 Dave Airlie <airlied@redhat.com> - 3.9.0-1
- llvm 3.9.0
- upstream moved where cmake files are packaged.
- upstream dropped CppBackend

* Wed Jul 13 2016 Adam Jackson <ajax@redhat.com> - 3.8.1-1
- llvm 3.8.1
- Add mips target
- Fix some shared library mispackaging

* Tue Jun 07 2016 Jan Vcelak <jvcelak@fedoraproject.org> - 3.8.0-2
- fix color support detection on terminal

* Thu Mar 10 2016 Dave Airlie <airlied@redhat.com> 3.8.0-1
- llvm 3.8.0 release

* Wed Mar 09 2016 Dan Horák <dan[at][danny.cz> 3.8.0-0.3
- install back memory consumption workaround for s390

* Thu Mar 03 2016 Dave Airlie <airlied@redhat.com> 3.8.0-0.2
- llvm 3.8.0 rc3 release

* Fri Feb 19 2016 Dave Airlie <airlied@redhat.com> 3.8.0-0.1
- llvm 3.8.0 rc2 release

* Tue Feb 16 2016 Dan Horák <dan[at][danny.cz> 3.7.1-7
- recognize s390 as SystemZ when configuring build

* Sat Feb 13 2016 Dave Airlie <airlied@redhat.com> 3.7.1-6
- export C++ API for mesa.

* Sat Feb 13 2016 Dave Airlie <airlied@redhat.com> 3.7.1-5
- reintroduce llvm-static, clang needs it currently.

* Fri Feb 12 2016 Dave Airlie <airlied@redhat.com> 3.7.1-4
- jump back to single llvm library, the split libs aren't working very well.

* Fri Feb 05 2016 Dave Airlie <airlied@redhat.com> 3.7.1-3
- add missing obsoletes (#1303497)

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 3.7.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Thu Jan 07 2016 Jan Vcelak <jvcelak@fedoraproject.org> 3.7.1-1
- new upstream release
- enable gold linker

* Wed Nov 04 2015 Jan Vcelak <jvcelak@fedoraproject.org> 3.7.0-100
- fix Requires for subpackages on the main package

* Tue Oct 06 2015 Jan Vcelak <jvcelak@fedoraproject.org> 3.7.0-100
- initial version using cmake build system
