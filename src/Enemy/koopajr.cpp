#include <Enemy/KoopaJr.hpp>
#include <JSystem/JGeometry.hpp>
#include <MarioUtil/MathUtil.hpp>
#include <math.h>

// TODO: everything above TDirectionCalc (TKoopaJr, TKoopaJrSubmarine and
// their nerves and params) is still missing from this TU.

// TODO: absDirection, sub and calcNearerDirection match apart from a 0x10-0x18
// bigger stack frame in the target, which hints at one more inline layer
// (likely an inline member wrapping this helper). calcTurnDirection also has a
// one-register swap after the std::fmodf call.

// fabricated: moves `direction` by a full turn if that brings it closer to
// `current`.
static inline void nearerDirection(f32 current, f32& direction)
{
	if (direction >= current) {
		f32 diff = direction - current;
		if (2.0f * M_PI - diff < diff)
			direction -= 2.0f * M_PI;
	} else {
		f32 diff = current - direction;
		if (2.0f * M_PI - diff < diff)
			direction += 2.0f * M_PI;
	}
}

TDirectionCalc::TDirectionCalc() { unk0 = 0.0f; }

TDirectionCalc::TDirectionCalc(f32 direction) { unk0 = direction; }

TDirectionCalc::TDirectionCalc(JGeometry::TVec3<f32> vec) { makeDirection(vec); }

void TDirectionCalc::normalize() { unk0 = MsWrapFmodf(unk0, 0.0f, 2.0f * M_PI); }

f32 TDirectionCalc::calcNearerDirection(f32 direction)
{
	normalize();
	nearerDirection(unk0, direction);
	return direction;
}

f32 TDirectionCalc::sub(f32 direction)
{
	unk0 = MsWrapMod(unk0, 0.0f, 2.0f * M_PI);
	f32 current = unk0;
	nearerDirection(current, direction);
	return current - direction;
}

f32 TDirectionCalc::calcTurnDirection(f32 target, f32 speed)
{
	normalize();
	unk0 = MsWrapMod(unk0, 0.0f, 2.0f * M_PI);
	f32 current = unk0;
	nearerDirection(current, target);
	f32 step = speed;
	if (target > current) {
		if (target - current < speed)
			step = target - current;
		return current + step;
	} else {
		if (current - target < speed)
			step = current - target;
		return current - step;
	}
}

void TDirectionCalc::makeDirection(JGeometry::TVec3<f32> vec)
{
	unk0 = atan2(vec.x, vec.z);
}

JGeometry::TVec3<f32> TDirectionCalc::calcDirectionVector()
{
	return JGeometry::TVec3<f32>(sin(unk0), 0.0f, cos(unk0));
}

f32 TDirectionCalc::absDirection(f32 direction)
{
	unk0 = MsWrapMod(unk0, 0.0f, 2.0f * M_PI);
	f32 current = unk0;
	nearerDirection(current, direction);
	return fabsf(current - direction);
}

f32 TDirectionCalc::d2r(f32 degrees) { return degrees * JGeometry::TUtil<f32>::PI() / 180.0f; }

f32 TDirectionCalc::r2d(f32 radians) { return 180.0f * radians / JGeometry::TUtil<f32>::PI(); }
