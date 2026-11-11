#version 330

in vec2 fragTexCoord;
in vec3 fragPos;
in vec3 fragNormal;
out vec4 outColor;

uniform vec3 u_shipPos;
uniform sampler2D u_texture;
uniform vec3 u_color = vec3(1.0);
uniform bool u_spotlightOn = true;

const vec3 lightDir = vec3(0.0, 0.0, -1.0);
const float innerCone = 0.985;
const float outerCone = 0.94;

void main()
{
    vec4 textureColor = texture(u_texture, fragTexCoord);

    if (textureColor.a < 0.1)
        discard;

    vec3 fromLight = fragPos - u_shipPos;
    float distanceToLight = length(fromLight);
    float angle = dot(fromLight / max(distanceToLight, 0.0001), lightDir);
    float intensity = smoothstep(outerCone, innerCone, angle);
    if (!u_spotlightOn)
        intensity = 0.0;


    vec3 normal = normalize(fragNormal);
    vec3 directionalLightDir = vec3(0.0, -1.0, 0.0);
    vec3 ambient = vec3(0.22);
    vec3 diffuse = vec3(0.25) * max(dot(normal, -directionalLightDir), 0.0);
    vec3 spotlight = vec3(0.9, 0.86, 0.72) * intensity;

    outColor = vec4(textureColor.rgb * u_color * (ambient + diffuse + spotlight),
                    textureColor.a);
}
