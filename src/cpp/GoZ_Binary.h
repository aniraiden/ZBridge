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

#ifndef __GOZ_BINARY_H__
#define __GOZ_BINARY_H__

/**
 ** GoZ Binary File Format
 ** The GoZ format starts with GoZb identifier ("GoZb") followed by 28 bytes of text.
 ** The actual mesh data blocks start at offset 32 from the begining of the file.
 **/


 ///////////////////////////////////////////////////////////////////////////////
 //////////////////////////////////////////////////////////////// GoZ_Header //
 /////////////////////////////////////////////////////////////////////////////
 // GoZ_Header is a 16 bytes header specfying the type of data inculded in each block

struct GoZ_Header
{
	unsigned int	tag;			// tag identifier
	unsigned int	size;			// the size (in bytes) of this data block, includeing this header
	unsigned int	iCount;			// items count
	float			modifier;		// this value depends on the type of block. If not used, then it is set to zero. 
};
//==========================
// GoZ_Subdiv stores info about subdivision and dynamic subdivision levels
//==========================
struct GoZ_SubDiv
{
	unsigned int	subdivLevles;				// how many subdivisions this mesh has. 0=No Subdiv
	unsigned int	currentSubdivLevel;			// which is the current subdiv level; 0=1st level,1=2nd level, etc.  
	unsigned int	dynamicSharpSubdiv;			// how many dynamic sharp  subdivisions this mesh has. 0=None
	unsigned int	dynamicSmoothSubdiv;		// how many dynamic smooth subdivisions this mesh has. 0=None
};
//==========================
//GoZ_FLAGS
//==========================
// The following flags are used by ZBrush to control the content of GoZ file to fit the target application
enum
{
	GoZ_VERTEX_FLIP_X = 1,
	GoZ_VERTEX_FLIP_Y = 2,
	GoZ_VERTEX_FLIP_Z = 4,
	GoZ_VERTEX_SWITCH_YZ = 8,
	GoZ_POLY_FLIP_NORMALS = 256,
	GoZ_UV_FLIP_U = 512,
	GoZ_UV_FLIP_V = 1024,
	GoZ_IMAGE_FLIP_V = 2048
};
// The following flags are used by ZBrush to on import to determine if remapping of mesh is needed. 
//ZBrush will not export these hints, it is only to be used by other Apps to notify ZBrush of possible changes.
enum
{
	GoZ_HINT_POINTS_CHANGED = 1,
	GoZ_HINT_UVS_CHANGED = 1,
	GoZ_HINT_FACES_CHANGED = 2,
	GoZ_HINT_NORMALS_CHANGED = 4,
	GoZ_HINT_TOPOLOGY_CHANGED = 8,
	GoZ_HINT_TEXTURE_MAP_CHANGED = 16,
	GoZ_HINT_NORMAL_MAP_CHANGED = 32,
	GoZ_HINT_DISPLACEMENT_MAP_CHANGED = 64,
	GoZ_HINT_COLOR_CHANGED = 128,
	GoZ_HINT_MESH_CHANGED = 256,	//indictes that the mesh has change and full remapping will be needed.
	GoZ_HINT_MESH_REPLACED = 512  //indictes that the mesh has change and is replacing the old mesh. No remapping will take place
};

//==========================
//GOZ Tags 
//==========================
enum
{
	GoZ_TAG_END_OF_FILE = 0,								// must be the last tag in the file. 16 bytes .
	GoZ_TAG_MESH,										//Mesh name. string size is the length of the string plus 1+Padding (for terminating Null and padding to 4 bytes boundry). 
	GoZ_TAG_MATERIAL,									//Material Name. string size is the length of the string plus 1+Padding (for terminating Null and padding to 4 bytes boundry).
//--------------------	
GoZ_TAG_BASE_ID_MODIFIERS = 5000,
GoZ_TAG_FLAGS,										// 4 bytes unsigned int . See GoZ_FLAGS values
GoZ_TAG_SUBDIV,										//  See GoZ_SubDiv struct
//--------------------	
GoZ_TAG_BASE_ID_POINT = 10000,
GoZ_TAG_POINT_LIST,									// 3 float values of x,y,z. each point takes 12 bytes exactly.
GoZ_TAG_DPOINT_LIST,								// 3 double float values of x,y,z. each point takes 24 bytes exactly. not yet supported
//GoZ_TAG_UVPOINT_LIST,								// Not yet supported. list of UV points which will be later indexed by GoZ_TAG_IUV4...
//--------------------	
GoZ_TAG_BASE_ID_EDGE = 15000,
//--------------------	
GoZ_TAG_BASE_ID_FACE = 20000,
GoZ_TAG_FACE4_LIST_FORMAT_1,						// first point is index 0, triangle represented by the 4th point set to -1. This is the preffered format for ZBrush. Each face takes 16 bytes exactly.
GoZ_TAG_FACE4_LIST_FORMAT_2,						// first point is index 0, triangle represented by the 4th point index equal to the 3rd point index. Each face takes 16 bytes exactly.
GoZ_TAG_FACE3_LIST,									// first point is index 0, Only 3 points per face (triangles).
//GoZ_TAG_FACEN_LIST,								// ngons. Not yet supported
//GoZ_TAG_FACE4_IUV4_LIST_FORMAT_1,					//Not yet supported
//GoZ_TAG_FACE4_IUV4_LIST_FORMAT_2,					//Not yet supported
//GoZ_TAG_FACE3_IUV3_LIST,							//Not yet supported
//GoZ_TAG_FACEN_IUVN_LIST,							//Not yet supported
//GoZ_TAG_FACE_EDGE_CREASE_LIST,					//Not yet supported		

//--------------------	
GoZ_TAG_BASE_UV = 25000,
GoZ_TAG_UV4_LIST,									// 4 (U,V) values per face
GoZ_TAG_UV3_LIST,									// 3 (U,V) values per triangle
//GoZ_TAG_UVN_LIST,										//  Not yet supported. ngons. 
//GoZ_TAG_IUV4_LIST,									//  Not yet supported. index into GoZ_TAG_UVPOINT_LIST.
//GoZ_TAG_IUV3_LIST,									//  Not yet supported. index into GoZ_TAG_UVPOINT_LIST. Not yet supported
//GoZ_TAG_IUVN_LIST,									//  Not yet supported. index into GoZ_TAG_UVPOINT_LIST. Not yet supported
//--------------------	
GoZ_TAG_BASE_ID_MASK = 30000,
GoZ_TAG_MASK8_LIST,										// 8 bit masking per vertex. 0xff=unmasked 0x00=fully masked
GoZ_TAG_MASK16_LIST,									// 16 bit masking per vertex. 0xffff=unmasked 0x0000=fully masked
//--------------------	
GoZ_TAG_BASE_ID_COLOR = 35000,
GoZ_TAG_MRGB_LIST,									// Material,red,green,blue per vertex. 8bits per channel.
//--------------------	
GoZ_TAG_BASE_ID_OTHER_DATA = 40000,
GoZ_TAG_GROUPS_LIST,								// 16 bits group ID per polygon.
GoZ_TAG_CREASE_LIST,								// 8 bits per polygon: (edge1 creased? 0x03 : 0) | (edge2 creased? 0x0C : 0) | (edge3 creased? 0x30 : 0) | (edge4 creased? 0xC0 : 0)
//--------------------	
GoZ_TAG_BASE_ID_TEXTURE_MAP = 45000,
GoZ_TAG_TEXTURE_MAP_PATH,						// optional relative-path filename for texture   image . The default image format is  .tif 24 bits. string size is the length of the string plus 1+Padding (for terminating Null and padding to 4 bytes boundry).
//--------------------	
GoZ_TAG_BASE_ID_NORMAL_MAP = 50000,
GoZ_TAG_NORMAL_MAP_PATH,						// optional relative-path filename for NormalMap image.  The default image format is  .tif 24 bits. string size is the length of the string plus 1+Padding (for terminating Null and padding to 4 bytes boundry).
//--------------------	
GoZ_TAG_BASE_ID_DISPLACEMENT_MAP = 55000,
GoZ_TAG_DISPLACEMENT_MAP_PATH,					// optional relative-path filename for DisplacementMap image. the modifier value contains the scaling factor for 16 bits displacement maps.  The default image format is .tif 16 bits. mid gray is zero displacement. string size is the length of the string plus 1+Padding (for terminating Null and padding to 4 bytes boundry).
//--------------------	
GoZ_TAG_BASE_ID_OTHER_MAP = 60000,
GoZ_TAG_MATCAP_PROXY_MAP_INLINE,				// iCount is the ((width<<16)+height), the modifier value is the Material index. The format is RGB 32 bits floating point value per channel. 0,0,0=black, 1,1,1=white. Note: RGB values may be outside of the zero-to-one range 
//--------------------	
GoZ_TAG_BASE_ID_ZBRUSH_PUBLIC = 65000,
//--------------------	
GoZ_TAG_BASE_ID_ZBRUSH_PRIVATE = 70000,
//--------------------	
GoZ_TAG_BASE_ID_3RD_PARTY_PUBLIC = 75000,
//--------------------	
GoZ_TAG_BASE_ID_3RD_PARTY_PRIVATE = 80000,
//--------------------	
GoZ_TAG_BASE_ID_IMPORT_ONLY = 90000,
//--------------------	
GoZ_TAG_BASE_ID_EXPORT_ONLY = 95000,
//--------------------	
GoZ_TAG_BASE_ID_HINTS = 100000,
//GoZ_TAG_CHANGED_HINTS,	// Not yet supported. see GoZ_HINT.

//--------------------	
//the following tags are not yet supported
GoZ_TAG_BASE_ID_FUTURE = 1000000,
//GoZ_TAG_NEW_MESH,								//Not yet supported. used when multiple objects are included within this file
//GoZ_TAG_MASK16_LIST,							//Not yet supported. 16 bit masking. 0xffff=unmasked 0x0000=fully masked. This will be available with ZBrush version 4
//GoZ_TAG_VERTEX_NORMAL,						//Not yet supported.
};

/*
//A Typical GoZ file contains the following blocks...
[ZBrush,GOZ_TAG_HEADER]					// GoZ header.				Size=32 bytes
[ZBrush,GoZ_TAG_MESH]					// Mesh name
[ZBrush,GOZ_TAG_FLAGS]					// flags.					Size=16+4 bytes.
[ZBrush,GOZ_TAG_POINT_LIST]				// list of x,y,z points.	Size= 16+(12*num of points) .			Note: The offset from beginning of file is guaranteed to be on 4 bytes boundary.
[ZBrush,GOZ_TAG_FACE4_LIST_FORMAT_1]	// list of faces. Triangels have the last index set to -1. Size= 16+(16*num of faces) bytes.		Note: The offset from beginning of file is guaranteed to be on 4 bytes boundary.
[ZBrush,GOZ_TAG_UV4_LIST]				// Included only if mesh has UVs assigned.   Size= 16+(32*num of faces) bytes.	Note: The offset from beginning of file is guaranteed to be on 4 bytes boundary.
[ZBrush,GoZ_TAG_MATERIAL]				// Material name
[ZBrush,GOZ_TAG_TEXTURE_MAP_PATH]		// Texture path. Included only if texture is assigned.   Size= 16+ (path Length+1) bytes.
[ZBrush,GOZ_TAG_NORMAL_MAP_PATH]		// Normal Map path. Included only if NormalMap is assigned.   Size= 16+ (path Length+1) bytes.
[ZBrush,GOZ_TAG_DISPLACEMENT_MAP_PATH]  // Displacement Map path. Included only if DisplacementMap is assigned.   Size= 16+ (path Length+1) bytes.
[ZBrush,GOZ_TAG_END_OF_FILE]			// must be the last block in te file. Size= 16 bytes.

*/
#endif  // __GOZ_BINARY_H__
