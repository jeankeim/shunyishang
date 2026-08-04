'use client'

import { useState, useEffect } from 'react'
import { Cloud, Sun, CloudRain, Wind, MapPin, Briefcase, Coffee, Heart, Users, Plane, Locate, Loader2, Dumbbell, GraduationCap, PartyPopper, Home, Gift, X } from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

// 场景时间段定义（用于智能排序）
const TIME_SLOTS: Record<string, { start: number; end: number }> = {
  '商务': { start: 9, end: 12 },
  '会议': { start: 10, end: 12 },
  '面试': { start: 9, end: 11 },
  '日常': { start: 8, end: 18 },
  '约会': { start: 18, end: 22 },
  '运动': { start: 6, end: 9 },
  '派对': { start: 20, end: 24 },
  '旅行': { start: 7, end: 19 },
  '居家': { start: 19, end: 24 },
  '婚礼': { start: 10, end: 16 },
}

// 常用场景定义 — ID 与后端 SCENE_ELEMENT_MAP 中文 key 完全一致
const COMMON_SCENES = [
  { id: '商务', label: '商务办公', icon: Briefcase, element: '金', desc: '专业沉稳' },
  { id: '会议', label: '会议汇报', icon: Users, element: '金', desc: '正式专业' },
  { id: '面试', label: '面试求职', icon: GraduationCap, element: '金', desc: '职业干练' },
  { id: '日常', label: '休闲日常', icon: Coffee, element: '土', desc: '舒适自然' },
  { id: '约会', label: '约会聚会', icon: Heart, element: '火', desc: '浪漫活力' },
  { id: '运动', label: '运动健身', icon: Dumbbell, element: '木', desc: '活力清爽' },
  { id: '旅行', label: '出行旅游', icon: Plane, element: '木', desc: '自由灵动' },
  { id: '派对', label: '派对聚会', icon: PartyPopper, element: '火', desc: '热情闪耀' },
  { id: '居家', label: '居家休闲', icon: Home, element: '土', desc: '温暖舒适' },
  { id: '婚礼', label: '婚礼婚宴', icon: Gift, element: '火', desc: '喜庆华丽' },
]

// 获取当前时间段的场景排序
function getSortedScenes(): typeof COMMON_SCENES {
  const hour = new Date().getHours()
  const usageFreq = getSceneUsageFrequency()

  return [...COMMON_SCENES].sort((a, b) => {
    const aFreq = usageFreq[a.id] || 0
    const bFreq = usageFreq[b.id] || 0
    const aSlot = TIME_SLOTS[a.id]
    const bSlot = TIME_SLOTS[b.id]
    const aInSlot = aSlot ? (hour >= aSlot.start && hour < aSlot.end ? 1 : 0) : 0
    const bInSlot = bSlot ? (hour >= bSlot.start && hour < bSlot.end ? 1 : 0) : 0

    // 1. 当前时间段优先
    if (aInSlot !== bInSlot) return bInSlot - aInSlot
    // 2. 使用频率次之
    if (aFreq !== bFreq) return bFreq - aFreq
    // 3. 默认顺序
    return 0
  })
}

// 场景使用频率（localStorage 持久化）
function getSceneUsageFrequency(): Record<string, number> {
  try {
    const data = localStorage.getItem('scene_usage_frequency')
    return data ? JSON.parse(data) : {}
  } catch {
    return {}
  }
}

function recordSceneUsage(sceneId: string) {
  try {
    const freq = getSceneUsageFrequency()
    freq[sceneId] = (freq[sceneId] || 0) + 1
    localStorage.setItem('scene_usage_frequency', JSON.stringify(freq))
  } catch {}
}

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

// 城市选择：改为可搜索输入框，数据源为后端 /weather/city-search
// （内置 120+ 城市 + 和风城市搜索 API，覆盖全国市县）

interface WeatherData {
  city: string
  temperature: number
  temperature_max?: number
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
  // 城市搜索（全国城市覆盖）
  const [cityQuery, setCityQuery] = useState('北京')
  const [cityMatches, setCityMatches] = useState<string[]>([])
  const [showCityDropdown, setShowCityDropdown] = useState(false)

  // 城市确定后同步输入框显示
  useEffect(() => {
    setCityQuery(city)
  }, [city])

  // 城市搜索防抖：输入 300ms 后调后端搜索接口
  useEffect(() => {
    const q = cityQuery.trim()
    if (!q || q === city) {
      setCityMatches([])
      return
    }
    const timer = setTimeout(async () => {
      try {
        const API_BASE = typeof window !== 'undefined' ? '' : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
        const res = await fetch(`${API_BASE}/api/v1/weather/city-search?q=${encodeURIComponent(q)}`)
        if (res.ok) {
          const data = await res.json()
          setCityMatches(data.matches || [])
          setShowCityDropdown(true)
        }
      } catch (e) {
        console.debug('[WeatherScene] 城市搜索失败:', e)
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [cityQuery, city])
    
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
      const API_BASE = typeof window !== 'undefined' ? '' : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
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

      // 方案1：后端坐标反查（和风城市搜索 API，覆盖全国市县，无需前端配 Key）
      try {
        const API_BASE = typeof window !== 'undefined' ? '' : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
        const res = await fetch(`${API_BASE}/api/v1/weather/reverse-geocode?lat=${lat}&lng=${lng}`)
        if (res.ok) {
          const data = await res.json()
          if (data.city) return data.city
        }
      } catch (e) {
        console.debug('后端坐标反查失败，尝试备用方案:', e)
      }

      // 方案2：使用高德地图API（如果有配置）
      const amapApiKey = process.env.NEXT_PUBLIC_AMAP_API_KEY;
      if (amapApiKey) {
        const city = await reverseGeocodeWithAmap(lat, lng, amapApiKey);
        if (city) return city;
      }

      // 方案3：使用本地算法（备用方案）
      const cityByCoords = getCityByCoords(lat, lng);
      if (cityByCoords) return cityByCoords;

      // 方案4：计算最近的城市
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

  // 初始加载：优先使用用户 preferred_city → 上次定位城市 → 浏览器定位 → 默认北京
  useEffect(() => {
    const initWeather = async () => {
      // 1. 尝试从后端获取用户 preferred_city
      try {
        const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
        if (token) {
          const API_BASE = typeof window !== 'undefined' ? '' : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
          const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${token}` }
          })
          if (res.ok) {
            const userData = await res.json()
            if (userData.preferred_city) {
              setCity(userData.preferred_city)
              fetchWeather(userData.preferred_city)
              return
            }
          }
        }
      } catch (e) {
        console.debug('[WeatherScene] 获取用户城市失败:', e)
      }

      // 2. 尝试使用上次定位的城市
      try {
        const historyStr = localStorage.getItem('weather_location_history')
        if (historyStr) {
          const history = JSON.parse(historyStr)
          if (history.length > 0) {
            const lastCity = history[0].city
            setCity(lastCity)
            fetchWeather(lastCity)
            return
          }
        }
      } catch (e) {
        console.debug('[WeatherScene] 读取定位历史失败:', e)
      }

      // 3. 尝试浏览器定位（静默，失败则回退北京）
      if (navigator.geolocation) {
        try {
          const position = await new Promise<GeolocationPosition>((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
              enableHighAccuracy: true,
              timeout: 8000,
              maximumAge: 600000  // 10分钟缓存
            })
          })
          const { latitude, longitude } = position.coords
          const cityName = await reverseGeocode(latitude, longitude)
          if (cityName) {
            setCity(cityName)
            fetchWeather(cityName)
            saveLocationHistory({ city: cityName, timestamp: Date.now(), coords: { lat: latitude, lng: longitude } })
            return
          }
        } catch (e) {
          console.debug('[WeatherScene] 初始定位失败，使用默认城市')
        }
      }

      // 4. 最终回退
      fetchWeather('北京')
    }

    initWeather()
  }, [])

  // 排序后的场景列表（按时间段 + 使用频率）
  const [sortedScenes, setSortedScenes] = useState(COMMON_SCENES)

  // 初始化排序
  useEffect(() => {
    setSortedScenes(getSortedScenes())
  }, [])

  // 处理场景选择（支持 toggle 取消）
  const handleSceneSelect = (sceneId: string, element: string) => {
    if (selectedScene === sceneId) {
      // 再次点击取消选择
      setSelectedScene('')
      onSceneChange?.('', '')
    } else {
      setSelectedScene(sceneId)
      onSceneChange?.(sceneId, element)
      recordSceneUsage(sceneId)
      setSortedScenes(getSortedScenes()) // 重新排序
    }
  }

  // 清除场景选择
  const handleClearScene = () => {
    setSelectedScene('')
    onSceneChange?.('', '')
  }

  // 获取天气图标
  const WeatherIcon = weather ? (WEATHER_ICONS[weather.weather] || Cloud) : Cloud

  return (
    <div className={cn('bg-white/80 backdrop-blur rounded-xl border border-[var(--brand-border)]/60 p-4 space-y-4', className)}>
      {/* 天气区域 */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Cloud className="h-4 w-4 text-[var(--wuxing-water)]" />
            <h3 className="font-medium text-[var(--brand-heading)]">今日天气</h3>
          </div>
          <div className="flex items-center gap-2">
            {/* 定位按钮 */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleLocate}
              disabled={locating}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded-md bg-[var(--brand-surface)] hover:bg-[var(--brand-surface-active)] transition-colors disabled:opacity-50 text-[var(--brand-body)]"
              title="自动定位"
            >
              {locating ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Locate className="h-3 w-3" />
              )}
              <span className="hidden sm:inline">{locating ? '定位中' : '定位'}</span>
            </motion.button>
            <div className="flex items-center gap-1 relative">
              <MapPin className="h-3 w-3 text-[var(--brand-subtle)]" />
              <input
                value={cityQuery}
                onChange={(e) => setCityQuery(e.target.value)}
                onFocus={() => { if (cityMatches.length > 0) setShowCityDropdown(true) }}
                onBlur={() => setTimeout(() => setShowCityDropdown(false), 150)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const q = cityQuery.trim()
                    if (q) {
                      handleManualCitySelect(q)
                      setShowCityDropdown(false)
                    }
                  }
                }}
                placeholder="搜索城市"
                title="输入城市名搜索（支持全国市县）"
                className="text-xs w-20 bg-transparent border-none outline-none text-[var(--brand-subtle)]"
              />
              {showCityDropdown && cityMatches.length > 0 && (
                <div className="absolute top-full right-0 mt-1 w-32 max-h-48 overflow-y-auto bg-white dark:bg-[var(--brand-surface)] rounded-lg border border-[var(--brand-border)] shadow-lg z-20">
                  {cityMatches.map((m) => (
                    <button
                      key={m}
                      onMouseDown={(e) => {
                        e.preventDefault()
                        handleManualCitySelect(m)
                        setShowCityDropdown(false)
                      }}
                      className="w-full text-left px-3 py-1.5 text-xs text-[var(--brand-body)] hover:bg-[var(--brand-surface-active)]"
                    >
                      {m}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 定位错误提示 */}
        {locationError && (
          <div className="mb-2 text-xs text-[var(--wuxing-earth)] dark:text-[var(--wuxing-earth)]">
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
                <WeatherIcon className="h-8 w-8 text-[var(--wuxing-water)]" />
                <div>
                  <div className="text-2xl font-semibold text-[var(--brand-heading)]">{weather.temperature}°</div>
                  <div className="text-xs text-[var(--brand-subtle)]">{weather.weather}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm">五行: <span className="font-medium text-[var(--wuxing-water)]">{weather.element}</span></div>
                <div className="text-xs text-[var(--brand-subtle)]">{weather.element_reason}</div>
              </div>
            </div>
            <div className="mt-2 flex gap-4 text-xs text-[var(--brand-subtle)]">
              <span>湿度: {weather.humidity}%</span>
              <span>风力: {weather.wind}</span>
            </div>
          </motion.div>
        )}
      </div>

      {/* 场景选择区域 */}
      <div className="pt-3 border-t border-[var(--brand-border)]/50">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-[var(--wuxing-wood)]" />
            <h3 className="font-medium text-[var(--brand-heading)]">常用场景</h3>
          </div>
          {selectedScene && (
            <button
              onClick={handleClearScene}
              className="flex items-center gap-1 text-xs text-[var(--brand-subtle)] hover:text-[var(--brand-heading)] transition-colors"
            >
              <X className="h-3 w-3" />
              清除选择
            </button>
          )}
        </div>
        
        <div className="grid grid-cols-2 gap-2">
          {sortedScenes.map((scene) => {
            const Icon = scene.icon
            const isSelected = selectedScene === scene.id
            const usageFreq = getSceneUsageFrequency()
            const isFrequent = (usageFreq[scene.id] || 0) >= 3
            const slot = TIME_SLOTS[scene.id]
            const hour = new Date().getHours()
            const isCurrentSlot = slot ? (hour >= slot.start && hour < slot.end) : false
            return (
              <motion.button
                key={scene.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleSceneSelect(scene.id, scene.element)}
                className={cn(
                  'relative flex items-center gap-2 p-2 rounded-lg border text-left transition-all duration-200',
                  isSelected
                    ? 'border-[hsl(var(--primary))] bg-[var(--brand-surface)] shadow-sm'
                    : 'border-[var(--brand-border)]/60 hover:border-[hsl(var(--primary))]/50 hover:bg-[var(--brand-surface-active)]'
                )}
              >
                <Icon className={cn('h-4 w-4 shrink-0', isSelected ? 'text-[hsl(var(--primary))]' : 'text-[#8A9F92]')} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate text-[var(--brand-heading)]">{scene.label}</div>
                  <div className="text-[10px] text-[var(--brand-subtle)]">{scene.desc} · {scene.element}</div>
                </div>
                {isCurrentSlot && !isSelected && (
                  <span className="absolute top-0.5 right-0.5 text-[9px] px-1 rounded bg-[var(--wuxing-wood)]/10 text-[var(--wuxing-wood)]">当前</span>
                )}
                {isFrequent && !isCurrentSlot && (
                  <span className="absolute top-0.5 right-0.5 text-[9px] px-1 rounded bg-[var(--wuxing-water)]/10 text-[var(--wuxing-water)]">常用</span>
                )}
              </motion.button>
            )
          })}
        </div>
      </div>

      {/* 综合建议提示 */}
      {weather && selectedScene && (
        <div className="pt-3 border-t border-border/50">
          <div className="text-xs text-[var(--brand-subtle)]">
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
