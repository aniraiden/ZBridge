/*
	Copyright (c)2011 - Pixologic Inc. All rights reserved.

  All title and intellectual property rights in and to the SDK and any copies of the SDK,
  are owned by Licensor.
  All title and intellectual property rights in and to the content which may be accessed
  through use of the SDK is the property of the respective content owner and may be protected
  by applicable copyright or other intellectual property laws and treaties.
  This Agreement grants you no rights to use such content.

	NO WARRANTIES. Licensor expressly disclaims any warranty for the SDK.
  THE SDK AND ANY RELATED DOCUMENTATION IS PROVIDED «AS IS» WITHOUT WARRANTY OF ANY KIND,
  EITHER EXPRESS OR IMPLIED, INCLUDING, WITHOUT LIMITATION, THE IMPLIED WARRANTIES
  OR MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, OR NONINFRINGEMENT.
  THE ENTIRE RISK ARISING OUT OF USE OR PERFORMANCE OF THE SDK REMAINS WITH YOU.
	
	BY INSTALLING, COPYING, OR USING THE SDK, YOU AGREE TO BE BOUND BY THE TERMS OF THIS AGREEMENT.
  IF YOU DO NOT AGREE TO THE TERMS OF THIS AGREEMENT, DO NOT INSTALL OR USE THE SDK.
*/

#ifndef __GOZ_CONFIG_H__
#define __GOZ_CONFIG_H__


// Retreives the rigth OS
#if defined(_WIN64)
#define GOZ_WIN

#elif defined(_WIN32)
#define GOZ_WIN

#else   // OS
#define GOZ_MAC
#endif  // OS



// Defines some specific types depending on the OS
#ifdef  GOZ_WIN
#pragma warning (disable:4996)
#include <windows.h>
typedef DWORD GoZ_ProcessID;

#else   // GOZ_MAC
#include <Carbon/Carbon.h>
typedef ProcessSerialNumber GoZ_ProcessID;
#endif  // GOZ_OS


#endif  // __GOZ_CONFIG_H__
