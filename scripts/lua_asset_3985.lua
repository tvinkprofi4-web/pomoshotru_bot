local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer
local RunService = game:GetService("RunService")

local function getClosestTarget()
    local closestTarget = nil
    local shortestDistance = 50

    for _, player in pairs(Players:GetPlayers()) do
        if player ~= LocalPlayer and player.Character and player.Character:FindFirstChild("HumanoidRootPart") and LocalPlayer.Character and LocalPlayer.Character:FindFirstChild("HumanoidRootPart") then
            local distance = (LocalPlayer.Character.HumanoidRootPart.Position - player.Character.HumanoidRootPart.Position).Magnitude
            if distance < shortestDistance then
                shortestDistance = distance
                closestTarget = player.Character
            end
        end
    end
    return closestTarget
end

RunService.Heartbeat:Connect(function()
    if LocalPlayer.Character and LocalPlayer.Character:FindFirstChild("HumanoidRootPart") then
        local target = getClosestTarget()
        
        if target and target:FindFirstChild("Humanoid") then
            if LocalPlayer.Character:FindFirstChildOfClass("Tool") then
                -- Логика атаки через инструмент
                target.Humanoid:TakeDamage(10)
            else
                -- Прямой вызов урона, если инструмента нет
                target.Humanoid:TakeDamage(10)
            end
        end
    end
end)