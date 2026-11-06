/* Session telemetry. Never persists device credentials or readings. */
(function (root) {
  'use strict';
  const MAX_SAMPLES = 720;
  function append(samples, sample) {
    if (!Number.isFinite(sample.time) || sample.values.length !== 4 || !sample.values.every((value,index)=>Number.isFinite(value)||(index===1&&value===null))) throw Error('Invalid telemetry sample');
    samples.push(sample);
    if (samples.length > MAX_SAMPLES) samples.splice(0, samples.length - MAX_SAMPLES);
  }
  function windowed(samples, minutes, now) {
    return samples.filter(s => !minutes || s.time >= now - minutes * 60000);
  }
  function summarize(samples, index) {
    const values = samples.map(s => s.values[index]).filter(Number.isFinite);
    return values.length ? { min: Math.min(...values), max: Math.max(...values), avg: values.reduce((a,b)=>a+b,0)/values.length } : null;
  }
  function segments(samples, index, start, end, low, high) {
    const result = []; let segment = [], last = null;
    for (const sample of samples) {
      if (!Number.isFinite(sample.values[index])) { if(segment.length) result.push(segment); segment=[]; last=null; continue; }
      if (last !== null && sample.time-last > 15000 && segment.length) {result.push(segment); segment=[];}
      segment.push([54+(sample.time-start)/Math.max(1,end-start)*620, 180-(sample.values[index]-low)/(high-low)*152]);
      last=sample.time;
    }
    if(segment.length) result.push(segment);
    return result;
  }
  function csv(samples) {
    return ['timestamp_utc,soil_moisture_percent,soil_temperature_c,air_temperature_c,humidity_percent,pump_command', ...samples.map(s=>[new Date(s.time).toISOString(), ...s.values, s.pump ? 1 : 0].join(','))].join('\r\n');
  }
  const api={append,windowed,summarize,segments,csv};
  if(typeof module!=='undefined')module.exports=api;else root.TelemetryHistory=api;
})(typeof window!=='undefined'?window:globalThis);
