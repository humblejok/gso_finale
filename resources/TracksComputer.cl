#if defined(cl_khr_fp64)  // Khronos extension available?
	#pragma OPENCL EXTENSION cl_khr_fp64 : enable
#elif defined(cl_amd_fp64)  // AMD extension available?
	#pragma OPENCL EXTENSION cl_amd_fp64 : enable
#endif
__kernel void performances(	__global const ACTIVE_PRECISION *values,
							__global ACTIVE_PRECISION *result) {
	int gid = get_global_id(0);
	if (gid!=0) {
		result[gid] = (values[gid] / values[gid - 1]) - 1.0;
	}
}
