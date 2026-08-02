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

#ifndef __GOZ_MESH_H__
#define __GOZ_MESH_H__

#include "GoZ_Utils.h"

class GoZ_Mesh
{
public:
    GoZ_Mesh();
    ~GoZ_Mesh();
    void clear();
    bool readMesh(const char *fileName);
    bool writeMesh(const char *fileName);


public:
	// Mesh name, might be NULL if not defined.
	// It's defined in the bloc GoZ_TAG_MESH in GoZ file format (GoZ_Binary.h).
	// String size is the length of the string plus 1+Padding (for terminating Null and padding to 4 bytes boundry).
    char           *m_name;
	// Material name, might be NULL if not defined
	// It's defined in the bloc GoZ_TAG_MATERIAL in GoZ file format (GoZ_Binary.h).
	// String size is the length of the string plus 1+Padding (for terminating Null and padding to 4 bytes boundry).
    char           *m_material;
	// This is a bitmask of misc I/O flags to flip axes, uvs, etc...
	// It's defined in the bloc GoZ_TAG_FLAGS in GoZ file format (GoZ_Binary.h).
	// More details by searching GoZ_FLAGS in GoZ_Binary.h
    unsigned int    m_flags;
	// The vertices coordinates (3 floats per vertex).
	// It's defined in the bloc GoZ_TAG_POINT_LIST in GoZ file format (GoZ_Binary.h)
	// - m_vertexCount: the vertices count
	// - m_vertices is: [x1 y1 z1 x2 y2 z2 ... xn yn zn], n being the vertex count.
    int             m_vertexCount;
    float          *m_vertices;
	// The faces (could be either all triangles, or a mix of both triangles and quads).
	// It's defined in any of the blocs GoZ_TAG_FACE4_LIST_FORMAT_1, GoZ_TAG_FACE4_LIST_FORMAT_2 or GoZ_TAG_FACE3_LIST in GoZ file format (GoZ_Binary.h).
	// Prefered format is GoZ_TAG_FACE4_LIST_FORMAT_1 (ZBrush will export faces in this format by default).
	// - m_faceCount: the faces count
	// - m_faceType: the faces format (GoZ_TAG_FACE4_LIST_FORMAT_1, GoZ_TAG_FACE4_LIST_FORMAT_2 or GoZ_TAG_FACE3_LIST)
	// - m_vertexIndices: the faces stored as consecutive vertex indices. Interpretation depends on faces format:
	//   - GoZ_TAG_FACE3_LIST: all faces are triangles, there are 3*n vertex indices, all packed 3 by 3, n being the faces count.
	//     for example, vertex indices are [v1 v2 v3  v3 v2 v4 ... vi vj vk], meaning faces are: triangle(v1,v2,v3), triangle(v3,v2,v4), ..., triangle(vi,vj,vk)
	//   - GoZ_TAG_FACE4_LIST_FORMAT_1: faces are a mix of triangles and quads, there are 4*n vertex indices, packed 4 by 4, the 4th index being -1 in case of a triangle.
	//     for example, vertex indices are [v1 v2 v3 v4  v4 v3 v5 -1 ... vi vj vk vl], meaning faces are: quad(v1,v2,v3,v4), triangle(v4,v3,v5), ..., quad(vi,vj,vk,vl)
	//   - GoZ_TAG_FACE4_LIST_FORMAT_2: faces are a mix of triangles and quads, there are 4*n vertex indices, packed 4 by 4, the 4th index being same as 3rd index in case of a triangle.
	//     for example, vertex indices are [v1 v2 v3 v4  v4 v3 v5 v5 ... vi vj vk vl], meaning faces are: quad(v1,v2,v3,v4), triangle(v4,v3,v5), ..., quad(vi,vj,vk,vl)
    int             m_faceCount;
    int             m_faceType;
    int            *m_vertexIndices;
	// The face uvs consists on separate uv coordinates per face (could be either 4 uvs per face or 3 uvs per face, depending wether faces are all triangles or not).
	// It's defined in any of the blocs GoZ_TAG_UV4_LIST or GoZ_TAG_UV3_LIST in GoZ file format (GoZ_Binary.h).
	// - m_uvFaceType: the uv-faces format (GoZ_TAG_UV4_LIST or GoZ_TAG_UV3_LIST)
	//   Note that this must match face format:
	//   - GoZ_TAG_UV3_LIST if face format is GoZ_TAG_FACE3_LIST
	//   - GoZ_TAG_UV4_LIST if face format is GoZ_TAG_FACE4_LIST_FORMAT_1 or GoZ_TAG_FACE4_LIST_FORMAT_2
	// - m_uvs: the uvs coordinates are stored per-face, as consecutive uv coordinates. Could be NULL if not defined.
	//   Interpretation depends on uv-faces format:
	//   - GoZ_TAG_UV3_LIST: there are 6*n values, all packed 6 by 6, n being the faces count.
	//     for example, uvs are [u1 v1 u2 v2 u3 v3  u4 v4 u5 v5 u6 v6 ... u3n-2 v3n-2 u3n-1 v3n-1 u3n v3n], meaning that:
	//     - uv-coordinates for face 1 = ((u1,v1), (u2,v2), (u3,v3))
	//     - uv-coordinates for face 2 = ((u4,v4), (u5,v5), (u6,v6))
	//     ...
	//     - uv-coordinates for face n = ((u3n-2,v3n-2), (u3n-1,v3n-1), (u3n,v3n))
	//   - GoZ_TAG_UV4_LIST: there are 8*n values, all packed 8 by 8, n being the faces count.
	//     for example, uvs are [u1 v1 u2 v2 u3 v3 u4 v4  u5 v5 u6 v6 u7 v7 u8 v8 ... u4n-3 v4n-3 u4n-2 v4n-2 u4n-1 v4n-1 u4n v4n], meaning that:
	//     - uv-coordinates for face 1 = ((u1,v1), (u2,v2), (u3,v3), (u4,v4))
	//     - uv-coordinates for face 2 = ((u5,v5), (u6,v6), (u7,v7), (u8,v8))
	//     ...
	//     - uv-coordinates for face n = ((u4n-3,v4n-3), (u4n-2,v4n-2), (u4n-1,v4n-1), (u4n,v4n))
	//     Note that in GoZ_TAG_UV4_LIST format, faces are stored as a mix of triangles and quads (GoZ_TAG_FACE4_LIST_FORMAT_1 or GoZ_TAG_FACE4_LIST_FORMAT_2),
	//     so the last uv coordinates (ie either (u4,v4), (u8,v8) ... or (u4n,v4n)) could be meaningful or not, depending wether each face is a quad or a triangle.
	int             m_uvFaceType;
    float          *m_uvs;
	// Mask information per-vertex (one 16-bit value per vertex), could be NULL if not defined
	// It's defined in the bloc GoZ_TAG_MASK16_LIST in GoZ file format (GoZ_Binary.h).
	// Each value is a 16 bit masking per vertex: 0xffff=unmasked, 0x0000=fully masked.
	unsigned short *m_mask;
	// Color information per-vertex (one 32-bit value per vertex), could be NULL if not defined
	// It's defined in the bloc GoZ_TAG_MRGB_LIST in GoZ file format (GoZ_Binary.h).
	// Material, Red, Green and Blue 8-bit channels are packed in a single 32-bit value per vertex.
    unsigned int   *m_mrgb;
	// Polygroup ID per-face (one 16-bit value per face), could be NULL if not defined.
	// It's defined in the bloc GoZ_TAG_GROUPS_LIST in GoZ file format (GoZ_Binary.h).
    short          *m_groups;
	// Creasing information per-face (one 8-bit value per face), could be NULL if not defined.
	// It's defined in the bloc GoZ_TAG_CREASE_LIST in GoZ file format (GoZ_Binary.h).
	// Each value stores a bitmask of the face's edges creasing: bits = e4 e4 e3 e3 e2 e2 e1 e1, where ei=1 if edge i is creased, 0 if not.
	// For example, let's consider a face i:
	// 1- case of face i being triangle (A,B,C):
    //    - edge [A,B] is creased if ((m_crease[i]&0x03)!=0)
    //    - edge [B,C] is creased if ((m_crease[i]&0x0C)!=0)
    //    - edge [C,A] is creased if ((m_crease[i]&0x30)!=0)
	// 2- case of face i being quad (A,B,C,D):
    //    - edge [A,B] is creased if ((m_creases[i]&0x03)!=0)
    //    - edge [B,C] is creased if ((m_creases[i]&0x0C)!=0)
    //    - edge [C,D] is creased if ((m_creases[i]&0x30)!=0)
    //    - edge [D,A] is creased if ((m_creases[i]&0xC0)!=0)
	// Then, we can simply consider that a unique edge is creased if all occurences of this edge in the faces are all creased.
	// For example, let's consider that edge [C,D] is shared by face i (A,B,C,D) and by face j (D,C,E), then:
	// unique edge [C,D] is creased if ( ((m_crease[i]&0x30)!=0) && ((m_crease[j]&0x03)!=0))
    char           *m_crease;
	// Path to the diffuse map, could be NULL if not defined.
	// It's defined in the bloc GoZ_TAG_TEXTURE_MAP_PATH in GoZ file format (GoZ_Binary.h).
	// String size is the length of the string plus 1+Padding (for terminating Null and padding to 4 bytes boundry).
    char           *m_diffuseMap;
	// Path to the normal map, could be NULL if not defined.
	// It's defined in the bloc GoZ_TAG_NORMAL_MAP_PATH in GoZ file format (GoZ_Binary.h).
	// String size is the length of the string plus 1+Padding (for terminating Null and padding to 4 bytes boundry).
    char           *m_normalMap;
	// Path to the displacement map, could be NULL if not defined.
	// It's defined in the bloc GoZ_TAG_DISPLACEMENT_MAP_PATH in GoZ file format (GoZ_Binary.h).
	// String size is the length of the string plus 1+Padding (for terminating Null and padding to 4 bytes boundry).
	// There's also an extra information: the displacement scale (a 32-bit float value).
    char           *m_displacementMap;
    float           m_displacementScale;
};

#endif  // __GOZ_MESH_H__
