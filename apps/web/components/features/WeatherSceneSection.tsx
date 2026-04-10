'use client'

import { useState, useEffect } from 'react'
import { Cloud, Sun, CloudRain, Wind, MapPin, Briefcase, Coffee, Heart, Users, Plane, Locate, Loader2 } from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

// 常用场景定义
const COMMON_SCENES = [
  { id: 'work', label: '职场办公', icon: Briefcase, element: '金', desc: '正式、专业' },
  { id: 'date', label: '约会聚会', icon: Heart, element: '火', desc: '浪漫、热情' },
  { id: 'casual', label: '休闲日常', icon: Coffee, element: '木', desc: '舒适、自然' },
  { id: 'business', label: '商务会议', icon: Users, element: '土', desc: '稳重、可靠' },
  { id: 'travel', label: '出行旅游', icon: Plane, element: '水', desc: '随性、流动' },
]

// 天气图标映射
const WEATHER_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  '晴': Sun,
  '多云': Cloud,
  '阴': Cloud,
  '雨': CloudRain,
  '小雨': CloudRain,
  '中雨': CloudRain,
  '大雨': CloudRain,
  '雷阵雨': CloudRain,
  '雪': CloudRain,
  '风': Wind,
}

// 常用城市列表
const COMMON_CITIES = ['北京', '上海', '广州', '深圳', '杭州', '成都']

interface WeatherData {
  city: string
  temperature: number
  weather: string
  humidity: number
  wind: string
  element: string
  element_reason: string
}

interface WeatherSceneSectionProps {
  onSceneChange?: (scene: string, sceneElement: string) => void
  onWeatherChange?: (weather: WeatherData) => void
  className?: string
}

export function WeatherSceneSection({ 
  onSceneChange, 
  onWeatherChange,
  className 
}: WeatherSceneSectionProps) {
  const [weather, setWeather] = useState<WeatherData | null>(null)
  const [selectedScene, setSelectedScene] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [city, setCity] = useState('北京')
  const [locating, setLocating] = useState(false)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [locationHistory, setLocationHistory] = useState<LocationRecord[]>([])
    
  // 定位记录类型
  interface LocationRecord {
    city: string
    timestamp: number
    coords?: { lat: number; lng: number }
  }
  
  // 初始化时加载定位历史
  useEffect(() => {
    loadLocationHistory()
  }, [])
  
  // 加载定位历史
  const loadLocationHistory = () => {
    try {
      const historyStr = localStorage.getItem('weather_location_history')
      if (historyStr) {
        const history = JSON.parse(historyStr)
        setLocationHistory(history.slice(0, 5)) // 只保留最近5条记录
      }
    } catch (error) {
      console.warn('加载定位历史失败:', error)
    }
  }
  
  // 保存定位历史
  const saveLocationHistory = (record: LocationRecord) => {
    try {
      const newHistory = [record, ...locationHistory.filter(item => item.city !== record.city)]
        .slice(0, 5) // 最多保留5条记录
        
      localStorage.setItem('weather_location_history', JSON.stringify(newHistory))
      setLocationHistory(newHistory)
    } catch (error) {
      console.warn('保存定位历史失败:', error)
    }
  }
  
  // 获取天气
  const fetchWeather = async (cityName: string) => {
    setLoading(true)
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${API_BASE}/api/v1/weather/weather?city=${encodeURIComponent(cityName)}`)
      if (response.ok) {
        const data = await response.json()
        setWeather(data)
        onWeatherChange?.(data)
      } else if (response.status === 502) {
        // 502 Bad Gateway - 服务暂时不可用，静默失败
        console.warn('[WeatherScene] 后端服务暂时不可用 (502)，请稍后重试')
      } else {
        console.error(`[WeatherScene] 获取天气失败: HTTP ${response.status}`)
      }
    } catch (e) {
      // 网络错误或 CORS 错误，静默失败
      console.warn('[WeatherScene] 获取天气失败（网络或服务不可用）:', e)
    } finally {
      setLoading(false)
    }
  }

  // 浏览器定位
  const handleLocate = async () => {
    if (!navigator.geolocation) {
      showLocationError('您的浏览器不支持定位功能', 'UNSUPPORTED')
      return
    }

    setLocating(true)
    setLocationError(null)

    try {
      // 获取GPS位置
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,  // 需要高精度以获得更好的城市识别
          timeout: 15000,            // 增加超时时间
          maximumAge: 300000         // 5分钟缓存
        })
      })

      const { latitude, longitude } = position.coords

      // 显示定位成功消息
      setLocationError('📍 定位成功，正在获取天气信息...')

      // 逆地理编码 - 将坐标转换为城市名
      const cityName = await reverseGeocode(latitude, longitude)
      
      if (cityName) {
        setCity(cityName)
        fetchWeather(cityName)
        
        // 保存定位历史
        saveLocationHistory({
          city: cityName,
          timestamp: Date.now(),
          coords: { lat: latitude, lng: longitude }
        })
        
        // 显示成功消息
        setTimeout(() => {
          setLocationError(null)
        }, 3000)
      } else {
        showLocationError('无法识别您的城市，请手动选择', 'CITY_NOT_FOUND')
      }
    } catch (error: any) {
      console.error('定位失败:', error)
      handleLocationError(error)
    } finally {
      setLocating(false)
    }
  }

  // 错误处理函数
  const handleLocationError = (error: GeolocationPositionError) => {
    switch (error.code) {
      case error.PERMISSION_DENIED:
        showLocationError(
          '位置权限被拒绝，请手动选择城市',
          'PERMISSION_DENIED'
        )
        break
      case error.POSITION_UNAVAILABLE:
        showLocationError(
          '无法获取位置信息（本地环境可能不支持定位），已使用默认城市：北京',
          'POSITION_UNAVAILABLE'
        )
        // 自动使用默认城市
        setTimeout(() => {
          setCity('北京')
          fetchWeather('北京')
        }, 2000)
        break
      case error.TIMEOUT:
        showLocationError(
          '定位超时，已使用默认城市：北京',
          'TIMEOUT'
        )
        // 自动使用默认城市
        setTimeout(() => {
          setCity('北京')
          fetchWeather('北京')
        }, 2000)
        break
      default:
        showLocationError(
          '定位失败，已使用默认城市：北京',
          'UNKNOWN_ERROR'
        )
        // 自动使用默认城市
        setTimeout(() => {
          setCity('北京')
          fetchWeather('北京')
        }, 2000)
        break
    }
  }

  // 显示错误信息
  const showLocationError = (message: string, type: string) => {
    setLocationError(message)
    // 3秒后自动清除错误信息
    setTimeout(() => {
      if (locationError?.includes(message)) {
        setLocationError(null)
      }
    }, 5000)
  }

  // 手动选择城市（清除错误）
  const handleManualCitySelect = (cityName: string) => {
    setCity(cityName)
    fetchWeather(cityName)
    setLocationError(null)
  }

  // 逆地理编码 - 优先使用高德地图API，回退到本地算法
  const reverseGeocode = async (lat: number, lng: number): Promise<string | null> => {
    try {
      // 检查是否在中国境内
      if (!isLocationInChina(lat, lng)) {
        throw new Error('当前位置不在中国境内');
      }

      // 方案1：使用高德地图API（如果有配置）
      const amapApiKey = process.env.NEXT_PUBLIC_AMAP_API_KEY;
      if (amapApiKey) {
        const city = await reverseGeocodeWithAmap(lat, lng, amapApiKey);
        if (city) return city;
      }

      // 方案2：使用本地算法（备用方案）
      const cityByCoords = getCityByCoords(lat, lng);
      if (cityByCoords) return cityByCoords;

      // 方案3：计算最近的城市
      const nearestCity = await findNearestCity(lat, lng);
      return nearestCity;

    } catch (error) {
      console.error('逆地理编码失败:', error);
      return null;
    }
  };

  // 使用高德地图API进行逆地理编码
  const reverseGeocodeWithAmap = async (lat: number, lng: number, apiKey: string): Promise<string | null> => {
    try {
      const response = await fetch(
        `https://restapi.amap.com/v3/geocode/regeo?key=${apiKey}&location=${lng},${lat}&extensions=base`
      );
      
      if (!response.ok) return null;
      
      const data = await response.json();
      if (data.status === '1' && data.regeocode) {
        const address = data.regeocode.addressComponent;
        let city = address.city || address.province;
        
        // 清理城市名称
        if (city && city.endsWith('市')) {
          city = city.slice(0, -1);
        }
        
        return city || null;
      }
    } catch (error) {
      console.warn('高德API调用失败，使用备用方案:', error);
    }
    return null;
  };

  // 查找最近的城市
  const findNearestCity = async (lat: number, lng: number): Promise<string | null> => {
    const cities = [
      { name: '北京', lat: 39.9042, lng: 116.4074 },
      { name: '上海', lat: 31.2304, lng: 121.4737 },
      { name: '广州', lat: 23.1291, lng: 113.2644 },
      { name: '深圳', lat: 22.5431, lng: 114.0579 },
      { name: '杭州', lat: 30.2741, lng: 120.1551 },
      { name: '成都', lat: 30.5728, lng: 104.0668 },
      { name: '武汉', lat: 30.5928, lng: 114.3055 },
      { name: '西安', lat: 34.3416, lng: 108.9398 },
      { name: '南京', lat: 32.0603, lng: 118.7969 },
      { name: '天津', lat: 39.3434, lng: 117.3616 },
    ];

    let minDistance = Infinity;
    let nearestCity: string | null = null;

    for (const city of cities) {
      const distance = calculateDistance(lat, lng, city.lat, city.lng);
      if (distance < minDistance) {
        minDistance = distance;
        nearestCity = city.name;
      }
    }

    // 如果距离超过300公里，可能不在这些城市范围内
    return minDistance <= 300 ? nearestCity : null;
  };

  // 计算两点间距离（公里）
  const calculateDistance = (lat1: number, lng1: number, lat2: number, lng2: number): number => {
    const R = 6371; // 地球半径（公里）
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLng/2) * Math.sin(dLng/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  };

  // 判断坐标是否在中国境内
  const isLocationInChina = (lat: number, lng: number): boolean => {
    return lat >= 18 && lat <= 53 && lng >= 73 && lng <= 135;
  };

  // 根据坐标推断城市（简化版）
  const getCityByCoords = (lat: number, lng: number): string | null => {
    // 中国主要城市坐标范围（简化版）
    const cityBounds: Record<string, { lat: [number, number], lng: [number, number] }> = {
      '北京': { lat: [39.4, 41.0], lng: [115.4, 117.5] },
      '上海': { lat: [30.7, 31.9], lng: [120.9, 122.2] },
      '广州': { lat: [22.5, 23.9], lng: [112.9, 114.4] },
      '深圳': { lat: [22.4, 22.9], lng: [113.7, 114.7] },
      '杭州': { lat: [29.9, 30.6], lng: [119.9, 120.7] },
      '成都': { lat: [30.4, 30.9], lng: [103.8, 104.3] },
    }

    for (const [city, bounds] of Object.entries(cityBounds)) {
      if (lat >= bounds.lat[0] && lat <= bounds.lat[1] &&
          lng >= bounds.lng[0] && lng <= bounds.lng[1]) {
        return city
      }
    }

    // 无法识别具体城市，返回默认
    return null
  }

  // 初始加载
  useEffect(() => {
    fetchWeather(city)
  }, [])

  // 处理场景选择
  const handleSceneSelect = (sceneId: string, element: string) => {
    setSelectedScene(sceneId)
    onSceneChange?.(sceneId, element)
  }

  // 获取天气图标
  const WeatherIcon = weather ? (WEATHER_ICONS[weather.weather] || Cloud) : Cloud

  return (
    <div className={cn('bg-white/80 backdrop-blur rounded-xl border border-[#E8F0EB]/60 p-4 space-y-4', className)}>
      {/* 天气区域 */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Cloud className="h-4 w-4 text-[#4A90C4]" />
            <h3 className="font-medium text-[#2D4A38]">今日天气</h3>
          </div>
          <div className="flex items-center gap-2">
            {/* 定位按钮 */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleLocate}
              disabled={locating}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded-md bg-[#F0F7F4] hover:bg-[#E8F5EC] transition-colors disabled:opacity-50 text-[#4A5F52]"
              title="自动定位"
            >
              {locating ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Locate className="h-3 w-3" />
              )}
              <span className="hidden sm:inline">{locating ? '定位中' : '定位'}</span>
            </motion.button>
            <div className="flex items-center gap-1">
              <MapPin className="h-3 w-3 text-[#6B7F72]" />
              <select
                value={city}
                onChange={(e) => {
                  handleManualCitySelect(e.target.value)
                }}
                className="text-xs bg-transparent border-none outline-none text-[#6B7F72] cursor-pointer"
              >
                {COMMON_CITIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* 定位错误提示 */}
        {locationError && (
          <div className="mb-2 text-xs text-amber-600 dark:text-amber-400">
            ⚠️ {locationError}
          </div>
        )}

        {weather && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-[#F0F7FA] rounded-lg p-3 border border-[#D4E8F0]/60"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <WeatherIcon className="h-8 w-8 text-[#4A90C4]" />
                <div>
                  <div className="text-2xl font-semibold text-[#2D4A38]">{weather.temperature}°</div>
                  <div className="text-xs text-[#6B7F72]">{weather.weather}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm">五行: <span className="font-medium text-[#4A90C4]">{weather.element}</span></div>
                <div className="text-xs text-[#6B7F72]">{weather.element_reason}</div>
              </div>
            </div>
            <div className="mt-2 flex gap-4 text-xs text-[#6B7F72]">
              <span>湿度: {weather.humidity}%</span>
              <span>风力: {weather.wind}</span>
            </div>
          </motion.div>
        )}
      </div>

      {/* 场景选择区域 */}
      <div className="pt-3 border-t border-[#E8F0EB]/50">
        <div className="flex items-center gap-2 mb-3">
          <Briefcase className="h-4 w-4 text-[#3DA35D]" />
          <h3 className="font-medium text-[#2D4A38]">常用场景</h3>
        </div>
        
        <div className="grid grid-cols-2 gap-2">
          {COMMON_SCENES.map((scene) => {
            const Icon = scene.icon
            const isSelected = selectedScene === scene.id
            return (
              <motion.button
                key={scene.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleSceneSelect(scene.id, scene.element)}
                className={cn(
                  'flex items-center gap-2 p-2 rounded-lg border text-left transition-all duration-200',
                  isSelected
                    ? 'border-[#3DA35D] bg-[#F0F7F4] shadow-sm'
                    : 'border-[#E8F0EB]/60 hover:border-[#3DA35D]/50 hover:bg-[#F5F9F7]'
                )}
              >
                <Icon className={cn('h-4 w-4', isSelected ? 'text-[#3DA35D]' : 'text-[#8A9F92]')} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate text-[#2D4A38]">{scene.label}</div>
                  <div className="text-[10px] text-[#6B7F72]">{scene.desc} · {scene.element}</div>
                </div>
              </motion.button>
            )
          })}
        </div>
      </div>

      {/* 综合建议提示 */}
      {weather && selectedScene && (
        <div className="pt-3 border-t border-border/50">
          <div className="text-xs text-[#6B7F72]">
            <span className="font-medium text-foreground">综合推荐：</span>
            今日天气属{weather.element}，{COMMON_SCENES.find(s => s.id === selectedScene)?.label}场景属
            {COMMON_SCENES.find(s => s.id === selectedScene)?.element}，
            将结合您的八字喜用神综合推荐
          </div>
        </div>
      )}
    </div>
  )
}
