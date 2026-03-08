/*
 *  This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

    ThePBone <tim.schneeberger(at)outlook.de> (c) 2020

    Design inspired by
    https://github.com/vipersaudio/viper4android_fx
 */

#include "LiquidEqualizerWidget.h"

#include "../3rdparty/JdspImpResToolbox.h"

LiquidEqualizerWidget::LiquidEqualizerWidget(QWidget *parent) : BaseLiquidEqualizerWidget(15, 21, 24000,  -12.0, 12.0, 128, 3, parent){}

LiquidEqualizerWidget::~LiquidEqualizerWidget(){}

void LiquidEqualizerWidget::computeCurve(const double *freqs, double *gains, int resolution, double *dispFreq, float *response)
{
    JdspImpResToolbox::ComputeEqResponse(freqs, gains, 1, resolution, dispFreq, response);
}

QVector<double> LiquidEqualizerWidget::getFrequencyPoints()
{
    return QVector<double>({ 25.0f, 40.0f, 63.0f, 100.0f, 160.0f, 250.0f, 400.0f, 630.0f, 1000.0f, 1600.0f, 2500.0f, 4000.0f, 6300.0f, 10000.0f, 16000.0f });
}


