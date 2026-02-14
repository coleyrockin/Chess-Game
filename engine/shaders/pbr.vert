#version 330

in vec3 in_position;
in vec3 in_normal;
in vec2 in_uv;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;
uniform mat4 uLightSpaceMatrix;

out vec3 vWorldPos;
out vec3 vNormal;
out vec2 vUv;
out vec4 vLightSpacePos;

void main() {
    vec4 world = uModel * vec4(in_position, 1.0);
    vWorldPos = world.xyz;
    vNormal = mat3(transpose(inverse(uModel))) * in_normal;
    vUv = in_uv;
    vLightSpacePos = uLightSpaceMatrix * world;
    gl_Position = uProjection * uView * world;
}
