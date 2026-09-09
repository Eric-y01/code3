export interface Step { key: string; label: string; status: 'pending' | 'running' | 'done' | 'error' }

export interface Meta {
  generated_at: string
  provider: string
  is_mock: boolean
  model_vision: string
  model_text: string
  image_url: string
  cutout_url?: string
  cutout_note?: string
  from_cache: boolean
  example_slug?: string
  report_id?: string
  user_input: { product_name: string; description: string }
}

export interface Product {
  product_name: string
  category: string
  appearance: { aspect: string; detail: string }[]
  style: string
  scenes: string[]
  user_provided: { field: string; value: string }[]
  visual_uncertainty: string[]
}

export interface Persona {
  name: string
  age_range: string
  occupation: string
  spending_power: string
  purchase_scenes: string[]
  motivations: string[]
  pain_points: string[]
  marketing_angle: string
}

export interface TitleVersion { title: string; rationale: string }

export interface Titles {
  taobao: TitleVersion
  jd: TitleVersion
  xiaohongshu: TitleVersion
}

export interface SellingPoint { title: string; detail: string }

export interface DetailSection { key: string; heading: string; content: string }

export interface Scene { no: number; time: string; visual: string; voiceover: string; focus: string }

export interface VideoScript {
  title: string
  hook: string
  format: string
  scenes: Scene[]
  ending_call: string
  hashtags: string[]
}

export interface ImagePlan {
  name: string
  ratio: string
  usage: string
  subject?: string
  scene?: string
  lighting?: string
  composition?: string
  style?: string
  prompt: string
  negative_prompt: string
  tip: string
}

export interface Report {
  meta: Meta
  product: Product
  persona: Persona
  titles: Titles
  selling_points: { items: SellingPoint[] }
  detail_sections: { sections: DetailSection[] }
  video_script: VideoScript
  image_plans: { plans: ImagePlan[] }
}

export interface TaskStatus {
  task_id: string
  status: string
  progress: number
  steps: Step[]
  current: string
  report?: Report
  report_id?: string
  error?: string
}

export interface Example {
  slug: string
  name: string
  tagline: string
  suggested_name: string
  description: string
  image_url: string
}

export interface AppConfig {
  provider: string
  is_mock: boolean
  has_api_key: boolean
  model_vision: string
  model_text: string
  steps: { key: string; label: string }[]
}
